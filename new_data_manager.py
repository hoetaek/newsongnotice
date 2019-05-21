import os
import json

class NewNotice:
    def __init__(self, json_file):
        self.filename = json_file
        if not os.path.exists(self.filename):
            with open(self.filename, 'w') as f:
                json.dump({'default_key':'default_value'}, f)
        with open(self.filename, 'r') as f:
            self.old_data = json.load(f)
            self.old_data.pop('default_key', None)
        self.new_data = dict()

    def compare_data(self, key, crawled_data, limit=200):
        self.crawled_data = crawled_data
        self.verify_key(key)
        value_data = self.old_data[key]
        new_data = [i for i in self.crawled_data if i not in value_data]
        if new_data:
            value_data.extend(new_data)
            self.limit_data(value_data, limit=limit)
            self.new_data = self.old_data
            self.save_data()
            return new_data
        else:
            return

    def verify_key(self, key):
        if key not in self.old_data:
            self.old_data[key] = []
            if self.new_data:
                self.new_data[key] = []

    def limit_data(self, data, limit):
        if len(data) > limit:
            del data[limit:]

    def save_data(self, key="", data=[]):
        if key and data:
            self.old_data[key] = data
            self.new_data = self.old_data
        if self.new_data:
            with open(self.filename, 'w') as f:
                json.dump(self.new_data, f)

    def get_data(self, key=""):
        if key:
            self.verify_key(key)
            return self.new_data[key] if self.new_data else self.old_data[key]
        return self.new_data if self.new_data else self.old_data
