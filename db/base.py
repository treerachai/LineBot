# -*- coding: utf-8 -*-

import pymongo

from collections import MutableMapping

class db_base(pymongo.collection.Collection):
    COLLECTION_NAME = '_id'
    SEQUENCE = '_seq'
    NOT_EXIST_SEQ_ID = -1

    def __init__(self, mongo_client_uri, db_name, collection_name, has_seq, index_col_list=None, codec_options=None, read_preference=None, write_concern=None, read_concern=None, **kwargs):
        self._has_seq = has_seq
        self._collection_name = collection_name

        mongo_client = pymongo.MongoClient(mongo_client_uri)

        self._db = mongo_client.get_database(db_name)
        super(db_base, self).__init__(self._db, collection_name, False, codec_options, read_preference, write_concern, read_concern, **kwargs)

        if index_col_list is None:
            index_col_list = []
        else:
            index_col_list = list(index_col_list)

        if not isinstance(index_col_list, (list, tuple)):
            raise ValueError('Column to make index must be list or tuple.')
        
        if collection_name not in self._db.collection_names() and has_seq:
            self._db.counter.insert({ db_base.COLLECTION_NAME: collection_name, db_base.SEQUENCE: 0 })

            if has_seq:
                index_col_list.append(db_base.SEQUENCE)
            
            self.create_index([(column, pymongo.DESCENDING) for column in index_col_list], unique=True)

    def insert_one(self, document, bypass_document_validation=False):
        inserted_seq_id = db_base.NOT_EXIST_SEQ_ID

        if self._has_seq:
            if db_base.SEQUENCE in document:
                raise ValueError('Remove _seq field to add sequence id.')

            document[db_base.SEQUENCE] = self._next_seq(self.name)
            inserted_seq_id = document[db_base.SEQUENCE]

        result = super(db_base, self).insert_one(document, bypass_document_validation)
        
        return ExtendedInsertOneResult(result.inserted_id, result.acknowledged, inserted_seq_id)

    def insert_many(self, documents, ordered=True, bypass_document_validation=False):
        inserted_seq_ids = []

        for document in documents:
            if self._has_seq:
                if db_base.SEQUENCE in document:
                    raise ValueError('Remove _seq field to add sequence id.')

                document[db_base.SEQUENCE] = self._next_seq(self.name)
                inserted_seq_ids.append(document[db_base.SEQUENCE])
            else:
                inserted_seq_ids.append(db_base.NOT_EXIST_SEQ_ID)

        result = super(db_base, self).insert_many(documents, ordered, bypass_document_validation)
        
        return ExtendedInsertManyResult(result.inserted_ids, result.acknowledged, inserted_seq_ids)

    def drop(self):
        self._db.counter.delete_many({ '_id': self._collection_name })
        return super(db_base, self).drop()

    def cursor_limit(self, cursor, limit=None, limit_default=None):
        if (isinstance(limit, (int, long)) ^ (limit is None)) and (isinstance(limit_default, (int, long)) ^ (limit_default is None)):
            if limit is not None:
                return cursor.limit(limit)
            elif limit_default is not None:
                return cursor.limit(limit_default)
            else:
                return cursor
        else:
            raise ValueError('Either limit default and limit must be integer or None to present "not set".')


    def _next_seq(self, collection_name):
        ret = self._db.counter.find_one_and_update({ db_base.COLLECTION_NAME: collection_name }, { '$inc': { db_base.SEQUENCE: 1 }}, None, None, True, pymongo.ReturnDocument.AFTER)
        return ret[db_base.SEQUENCE]

class dict_like_mapping(MutableMapping):
    def __init__(self, org_dict):
        if org_dict is None:
            self._dict = {}
        else:
            self._dict = dict(org_dict)

    def __getitem__(self, key):
        return self._dict[key]

    def __setitem__(self, key, value):
        self._dict[key] = value

    def __delitem__(self, key):
        del self._dict[key]

    def __iter__(self):
        return iter(self._dict)

    def __len__(self):
        return len(self._dict)

    def __repr__(self):
        return str(self._dict)

class ExtendedInsertOneResult(pymongo.results.InsertOneResult):
    def __init__(self, inserted_id, acknowledged, seq_id=None):
        if seq_id is None:
            self._seq_id = db_base.NOT_EXIST_SEQ_ID
        else:
            self._seq_id = seq_id

        super(ExtendedInsertOneResult, self).__init__(inserted_id, acknowledged)

    @property
    def inserted_seq_id(self):
        return self._seq_id

class ExtendedInsertManyResult(pymongo.results.InsertManyResult):
    def __init__(self, inserted_ids, acknowledged, inserted_seq_ids=None):
        if inserted_seq_ids is None:
            self._seq_ids = [db_base.NOT_EXIST_SEQ_ID for i in range(len(inserted_ids))]
        else:
            self._seq_ids = inserted_seq_ids
            
        return super(ExtendedInsertManyResult, self).__init__(inserted_ids, acknowledged)

    @property
    def inserted_seq_ids(self):
        return self._seq_ids
