# encoding:utf-8
# encoding:utf-8
from pymongo import MongoClient



class MongoConnect(object):
    def __init__(self, uri, db_name, collection_name):
        self._uri = uri
        self._db_name = db_name
        self._collection_name = collection_name
        self._mongo_client = MongoClient(self._uri)
        self.collection = self._mongo_client[self._db_name][self._collection_name]