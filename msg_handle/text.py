# -*- coding: utf-8 -*-

class text_msg(object):
    @staticmethod
    def split(text, splitter, size):
        list = []
  
        if text is not None:
            for i in range(size):
                if splitter not in text or i == size - 1:
                    list.append(text)
                    break
                list.append(text[0:text.index(splitter)])
                text = text[text.index(splitter)+len(splitter):]
  
        while len(list) < size:
            list.append(None)
        
        return list


