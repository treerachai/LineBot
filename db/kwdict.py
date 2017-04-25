# -*- coding: utf-8 -*-

import os

import urlparse
import psycopg2

import collections

class kw_dict_mgr(object):

    def __init__(self, scheme, db_url):
        urlparse.uses_netloc.append(scheme)
        self.url = urlparse.urlparse(db_url)
        self._set_connection()




    def sql_cmd_only(self, cmd):
        return self.sql_cmd(cmd, None)

    def sql_cmd(self, cmd, dict):
        self._set_connection()
        self.cur.execute(cmd, dict)
        try:
            result = self.cur.fetchall()
        except psycopg2.ProgrammingError as ex:
            if ex.message == 'no results to fetch':
                result = None
            else:
                raise ex
        
        self._close_connection()
        return result




    def create_kwdict(self):
        cmd = u'CREATE TABLE keyword_dict( \
                    {} SERIAL, \
                    {} VARCHAR(500), \
                    {} VARCHAR(500), \
                    {} BOOLEAN NOT NULL DEFAULT FALSE, \
                    {} BOOLEAN NOT NULL DEFAULT FALSE, \
                    {} BOOLEAN NOT NULL DEFAULT FALSE, \
                    {} INTEGER NOT NULL, \
                    {} VARCHAR(33) NOT NULL), \
                    {} BOOLEAN DEFAULT FALSE, \
                    {} BOOLEAN DEFAULT FALSE;'.format(*_col_list)
        result = self.sql_cmd_only(cmd)
        return True if len(result) <= 1 else False

    def insert_keyword(self, keyword, reply, creator_id, is_top, is_sticker_kw, is_pic_reply):
        keyword = keyword.replace('  ', ' ')
        reply = reply.replace('  ', ' ')
        if keyword == '' or reply == '':
            cmd = u'INSERT INTO keyword_dict(keyword, reply, creator, used_time, admin, is_sticker_kw, is_pic_reply) \
                    VALUES(%(kw)s, %(rep)s, %(cid)s, 0, %(sys)s, %(stk_kw)s, %(pic_rep)s) \
                    RETURNING *;'
            cmd_dict = {'kw': keyword, 'rep': reply, 'cid': creator_id, 'sys': is_top, 'stk_kw': is_sticker_kw, 'pic_rep': is_pic_reply}
            cmd_override = u'UPDATE keyword_dict SET override = TRUE \
                             WHERE keyword = %(kw)s'
            cmd_override_dict = {'kw': keyword}
            self.sql_cmd(cmd_override, cmd_override_dict)
            result = self.sql_cmd(cmd, cmd_dict)
            return result
        else:
            return None

    def get_reply(self, keyword, is_sticker_kw):
        keyword = keyword.replace('%', '')
        keyword = keyword.replace("'", r"'")
        cmd = u'SELECT * FROM keyword_dict \
                WHERE keyword = %(kw)s AND deleted = FALSE AND is_sticker_kw = %(stk_kw)s\
                ORDER BY admin DESC, id DESC;'
        db_dict = {'kw': keyword, 'stk_kw': is_sticker_kw}
        result = self.sql_cmd(cmd, db_dict)
        if len(result) > 0:
            cmd_update = u'UPDATE keyword_dict SET used_time = used_time + 1 WHERE id = %(id)s AND override = FALSE'
            cmd_update_dict = {'id': result[0][kwdict_col.id]}
            self.sql_cmd(cmd_update, cmd_update_dict)
            return result
        else:
            return None

    def search_keyword(self, keyword):
        cmd = u'SELECT * FROM keyword_dict WHERE keyword LIKE %(kw)s OR reply LIKE %(kw)s ORDER BY id DESC;'
        cmd_dict = {'kw': '%' + keyword + '%'}
        result = self.sql_cmd(cmd, cmd_dict)
        if len(result) > 0:
            return result
        else:
            return None

    def search_keyword_index(self, startIndex, endIndex):
        cmd = u'SELECT * FROM keyword_dict WHERE id >= %(si)s AND id <= %(ei)s ORDER BY id DESC;'
        cmd_dict = {'si': startIndex, 'ei': endIndex}
        result = self.sql_cmd(cmd, cmd_dict)
        if len(result) > 0:
            return result
        else:
            return None

    def get_info(self, keyword):
        cmd = u'SELECT * FROM keyword_dict WHERE keyword = %(kw)s OR reply = %(kw)s ORDER BY id DESC;'
        cmd_dict = {'kw': keyword}
        result = self.sql_cmd(cmd, cmd_dict)
        if len(result) > 0:
            return result
        else:
            return None

    def get_info_id(self, id):
        cmd = u'SELECT * FROM keyword_dict WHERE id = %(id)s ORDER BY id DESC;'
        cmd_dict = {'id': id}
        result = self.sql_cmd(cmd, cmd_dict)
        if len(result) > 0:
            return result
        else:
            return None

    def order_by_usedrank(self, limit=1000):
        cmd = u'SELECT *, RANK() OVER (ORDER BY used_time DESC) AS used_rank FROM keyword_dict ORDER BY used_rank ASC LIMIT %(limit)s;'
        cmd_dict = {'limit': limit}
        result = self.sql_cmd(cmd, cmd_dict)
        if len(result) > 0:
            return result
        else:
            return None

    def user_created_rank(self, limit=1000):
        """[0]=Rank, [1]=User ID, [2]=Count"""
        cmd = u'SELECT RANK() OVER (ORDER BY created_count DESC), * FROM (SELECT creator, COUNT(creator) AS created_count FROM keyword_dict GROUP BY creator ORDER BY created_count DESC) AS FOO LIMIT %(limit)s'
        cmd_dict = {'limit': limit}
        result = self.sql_cmd(cmd, cmd_dict)
        if len(result) > 0:
            return result
        else:
            return None


    def most_used(self):
        cmd = u'SELECT * FROM keyword_dict WHERE used_time = (SELECT MAX(used_time) FROM keyword_dict) AND override = FALSE AND deleted = FALSE;'
        result = self.sql_cmd_only(cmd)
        if len(result) > 0:
            return result
        else:
            return None

    def least_used(self):
        cmd = u'SELECT * FROM keyword_dict WHERE used_time = (SELECT MIN(used_time) FROM keyword_dict) AND override = FALSE AND deleted = FALSE;'
        result = self.sql_cmd_only(cmd)
        if len(result) > 0:
            return result
        else:
            return None

    def delete_keyword(self, keyword, is_top):
        cmd = u'UPDATE keyword_dict \
                SET deleted = TRUE \
                WHERE keyword = %(kw)s AND admin = %(top)s AND deleted = FALSE \
                RETURNING *;'
        cmd_dict = {'kw': keyword, 'top': is_top}
        result = self.sql_cmd(cmd, cmd_dict)
        if len(result) > 0:
            return result
        else:
            return None

    def delete_keyword_id(self, id, is_top):
        cmd = u'UPDATE keyword_dict \
                SET deleted = TRUE \
                WHERE id = %(id)s AND admin = %(top)s AND deleted = FALSE \
                RETURNING *;'
                
        cmd_dict = {'id': id, 'top': is_top}
        result = self.sql_cmd(cmd, cmd_dict)
        if len(result) > 0:
            return result
        else:
            return None

    def user_sort_by_created_pair(self):
        cmd = u'SELECT creator, COUNT(creator) FROM keyword_dict GROUP BY creator ORDER BY COUNT(creator) DESC;'
        result = self.sql_cmd_only(cmd)
        if len(result) > 0:
            return result
        else:
            return None




    def row_count(self):
        cmd = u'SELECT COUNT(id) FROM keyword_dict;'
        result = self.sql_cmd_only(cmd)
        return int(result[0][0])

    def picture_reply_count(self):
        cmd = u'SELECT COUNT(id) FROM keyword_dict WHERE is_pic_reply = TRUE;'
        result = self.sql_cmd_only(cmd)
        return int(result[0][0])

    def sticker_keyword_count(self):
        cmd = u'SELECT COUNT(id) FROM keyword_dict WHERE is_sticker_kw = TRUE;'
        result = self.sql_cmd_only(cmd)
        return int(result[0][0])

    def used_time_sum(self):
        cmd = u'SELECT SUM(used_time) FROM keyword_dict;'
        result = self.sql_cmd_only(cmd)
        return int(result[0][0])




    

    @staticmethod
    def sticker_png_url(sticker_id):
        return 'https://sdl-stickershop.line.naver.jp/stickershop/v1/sticker/{stk_id}/android/sticker.png'.format(stk_id=sticker_id)
    
    @staticmethod
    def sticker_id(sticker_url):
        return sticker_url.replace('https://sdl-stickershop.line.naver.jp/stickershop/v1/sticker/', '').replace('/android/sticker.png', '')
    
    @staticmethod
    def entry_basic_info(entry_row):
        text = u'ID: {id}\n'.format(id=entry_row[kwdict_col.id])
        kw = entry_row[kwdict_col.keyword].decode('utf8')
        if not entry_row[kwdict_col.is_sticker_kw]:
            text += u'Keyword: {kw}\n'.format(kw=kw)
        else:
            text += u'Keyword: (Sticker ID: {kw})\n'.format(kw=kw)
        text += u'Reply {rep_type}: {rep}'.format(rep=entry_row[kwdict_col.reply].decode('utf8'),
                                                  rep_type='Picture URL' if entry_row[kwdict_col.is_pic_reply] else 'Text')
        return text

    @staticmethod
    def entry_detailed_info(line_api, entry_row):
        basic = kw_dict_mgr.entry_basic_info(entry_row) + '\n\n'
        basic += u'Attribute: \n'
        basic += u'{top} {ovr} {delete}\n\n'.format(top='[ PINNED ]' if entry_row[kwdict_col.admin] else '[ - ]',
                                                   ovr='[ OVERRIDE ]' if entry_row[kwdict_col.override] else '[ - ]',
                                                   delete='[ DELETED ]' if entry_row[kwdict_col.deleted] else '[ - ]')
        basic += u'Called count: {ct}\n\n'.format(ct=entry_row[kwdict_col.used_time])

        profile = line_api.get_profile(entry_row[kwdict_col.creator])

        basic += u'Creator Name: {name}\n'.format(name=profile.display_name)
        basic += u'Creator user id: {uid}'.format(uid=entry_row[kwdict_col.creator])

        return basic
    
    @staticmethod
    def list_keyword(data, limit=25):
        """return two object to access by [\'limited\'] and [\'full\']."""
        ret = {'limited': '', 'full': ''}
        limited = False
        count = len(data)
        ret['full'] = 'Count of results: {num}\n\n'.format(num=count)

        for index, row in enumerate(data, start=1):
            text = 'ID: {id} - {kw} {ovr}{top}{delete}\n'.format(
                id=row[kwdict_col.id],
                kw='(Sticker {id})'.format(id=row[kwdict_col.keyword]) if row[kwdict_col.is_sticker_kw] else row[kwdict_col.keyword],
                ovr='(OVR)' if row[kwdict_col.override] else '',
                top='(TOP)' if row[kwdict_col.admin] else '',
                delete='(DEL)' if row[kwdict_col.deleted] else '')
            ret['full'] += text

            if not limited:
                ret['limited'] += text

                if index >= limit:
                    ret['limited'] += '...({num} more)'.format(num=count - limit)
                    limited = True

        return ret

    @staticmethod
    def list_keyword_info(line_api, data, limit=2):
        """return two object to access by [\'limited\'] and [\'full\']."""
        ret = {'limited': '', 'full': ''}
        limited = False
        count = len(data)
        separator = '====================\n'
        ret['full'] = 'Count of results: {num}\n'.format(num=count)

        for index, row in enumerate(data, start=1):
            text = separator
            text += kw_dict_mgr.entry_detailed_info(line_api, row)
            text += '\n'
            ret['full'] += text

            if not limited:
                ret['limited'] += text

                if index >= limit:
                    ret['limited'] += separator
                    ret['limited'] += '{num} not displayed.'.format(num=count - limit)
                    limited = True

        return ret

    @staticmethod
    def list_keyword_ranking(data):
        text = 'Top {num} called pair: '.format(num=limit)

        for index, row in enumerate(data, start=1):
            text += u'\nNo.{rk} - ID: {id} - {kw} ({ct})'.format(
                rk=row[kwdict_col.used_rank], 
                kw='(Sticker ID {id})'.format(id=row[kwdict_col.keyword]) if row[kwdict_col.is_sticker_kw] else row[kwdict_col.keyword].decode('utf8'), 
                id=row[kwdict_col.id],
                ct=row[kwdict_col.used_time])

        return text

    @staticmethod
    def list_user_created_ranking(line_api, data):
        text = 'Top {num} creative user: '.format(num=limit)

        for index, row in enumerate(data, start=1):
            text += u'\nNo.{rk} - {name} ({ct})'.format(
                rk=row[0],
                name=line_api.get_profile(row[1]).display_name,
                ct=row[2])

        return text



    def _close_connection(self):
        self.conn.commit()
        self.cur.close()
        self.conn.close()

    def _set_connection(self):
        self.conn = psycopg2.connect(
            database=self.url.path[1:],
            user=self.url.username,
            password=self.url.password,
            host=self.url.hostname,
            port=self.url.port
        )
        self.cur = self.conn.cursor()


_col_list = ['id', 'keyword', 'reply', 'deleted', 'override', 'admin', 'used_time', 'creator', 'is_pic_reply', 'is_sticker_kw', 'used_rank']
_col_tuple = collections.namedtuple('kwdict_col', _col_list)
kwdict_col = _col_tuple(0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10)
