__author__ = 'Administrator'

import sqlite3
import sys
import os

class DatabaseManager(object):
    conn = None

    def __init__(self):
        self.HWS_GATEWAY_DB = 'hws_gateway.db'
        self.DB_STORE_PATH = "/home/sqlite_db"

        self.CREATE_TABLE_SERVER_ID_MAPPING = \
            '''CREATE TABLE server_id_mapping(cascading_server_id text, cascaded_server_id text)'''
        self.INSERT_SERVER_ID_MAPPING = \
            '''INSERT INTO server_id_mapping(cascading_server_id, cascaded_server_id) VALUES (?,?)'''

        self.CREATE_TABLE_SERVER_ID_NAME_MAPPING = \
            '''CREATE TABLE server_id_name_mapping(cascading_server_id text, cascaded_server_name text)'''

        self.INSERT_SERVER_ID_NAME_MAPPING = \
            '''INSERT INTO server_id_name_mapping(cascading_server_id, cascaded_server_name) VALUES (?,?)'''

        self.CREATE_TABLE_IMAGE_ID_MAPPING = \
            '''CREATE TABLE image_id_mapping(cascading_image_id text, cascaded_image_id text)'''

        self.INSERT_IMAGE_ID_MAPPING = \
            '''INSERT INTO image_id_mapping(cascading_image_id, cascaded_image_id) VALUES (?,?)'''

        self.CREATE_TABLE_FLAVOR_ID_MAPPING = \
            '''CREATE TABLE flavor_id_mapping(cascading_flavor_id text, cascaded_flavor_id text)'''

        self.INSERT_TABLE_FLAVOR_ID_MAPPING = \
            '''INSERT INTO flavor_id_mapping(cascading_flavor_id, cascaded_flavor_id) VALUES (?,?)'''

        self.CREATE_TABLE_VOLUME_MAPPING = \
            '''CREATE TABLE volume_mapping(cascading_volume_id text, cascaded_volume_id text, cascaded_backup_id text, cascaded_image_id text)'''

        self.INSERT_VOLUME_MAPPING = \
            '''INSERT INTO volume_mapping(cascading_volume_id, cascaded_volume_id, cascaded_backup_id, cascaded_image_id) VALUES (?, ?, ?, ?)'''

        db_full_name = self.get_hws_gateway_db_full_name()
        if not os.path.isfile(db_full_name):
            self.init_database()

    def get_current_dir(self):
        return os.path.split(os.path.realpath(__file__))[0]

    def get_hws_gateway_db_full_name(self):
        full_name = os.path.join(self.DB_STORE_PATH, self.HWS_GATEWAY_DB)
        return full_name

    def connect(self):
        if DatabaseManager.conn is None:
            DatabaseManager.conn = sqlite3.connect(self.get_hws_gateway_db_full_name())

        return DatabaseManager.conn

    def close(self):
        if DatabaseManager.conn:
            DatabaseManager.conn.close()

        DatabaseManager.conn = None

    def commit(self):
        if DatabaseManager.conn:
            DatabaseManager.conn.commit()

    def init_database(self):
        self.create_table_server_id_mapping()
        self.create_table_server_id_name_mapping()
        self.create_table_image_id_mapping()
        self.create_table_flavor_id_mapping()
        self.create_table_volume_mapping()

    def add_server_id_mapping(self, cascading_server_id, cascaded_server_id):
        cursor = self.connect().cursor()
        exe_sql = self.INSERT_SERVER_ID_MAPPING
        cursor.execute(exe_sql, (cascading_server_id, cascaded_server_id))
        self.commit()

    def delete_server_id_by_cascading_id(self, cascading_server_id):
        cursor = self.connect().cursor()
        exe_sql = "DELETE FROM server_id_mapping WHERE cascading_server_id = ?"
        data = [cascading_server_id]
        cursor.execute(exe_sql, data)
        self.commit()

    def get_cascaded_server_id(self, cascading_id):
        cursor = self.connect().cursor()
        cursor.execute("SELECT cascaded_server_id FROM server_id_mapping "
                       "WHERE cascading_server_id = '%s'"
                                 % cascading_id)
        row = cursor.fetchone()
        if row:
            return str(row[0])

        return None

    def add_server_id_name_mapping(self, cascading_server_id, cascaded_server_name):
        cursor = self.connect().cursor()
        exe_sql = self.INSERT_SERVER_ID_NAME_MAPPING
        cursor.execute(exe_sql, (cascading_server_id, cascaded_server_name))
        self.commit()

    def get_cascaded_server_name(self, cascading_server_id):
        cursor = self.connect().cursor()
        cursor.execute("SELECT cascaded_server_name FROM server_id_name_mapping "
                       "WHERE cascading_server_id = '%s'" % cascading_server_id)
        row = cursor.fetchone()
        if row:
            return str(row[0])

        return None

    def delete_server_id_name_by_cascading_id(self, cascading_server_id):
        cursor = self.connect().cursor()
        exe_sql = "DELETE FROM server_id_name_mapping WHERE cascading_server_id = ?"
        data = [cascading_server_id]
        cursor.execute(exe_sql, data)
        self.commit()

    def add_image_id_mapping(self, cascading_image_id, cascaded_image_id):
        cursor = self.connect().cursor()
        exe_sql = self.INSERT_IMAGE_ID_MAPPING
        cursor.execute(exe_sql, (cascading_image_id, cascaded_image_id))
        self.commit()

    def delete_image_id_mapping(self, cascading_image_id):
        cursor = self.connect().cursor()
        exe_sql = "DELETE FROM image_id_mapping WHERE cascading_image_id = ?"
        data = [cascading_image_id]
        cursor.execute(exe_sql, data)
        self.commit()

    def get_cascaded_image_id(self, cascading_image_id):
        cursor = self.connect().cursor()
        cursor.execute("SELECT cascaded_image_id FROM image_id_mapping "
                       "WHERE cascading_image_id = '%s'" % cascading_image_id)
        row = cursor.fetchone()
        if row:
            return str(row[0])

        return None

    def add_flavor_id_mapping(self, cascading_flavor_id, cascaded_flavor_id):
        cursor = self.connect().cursor()
        exe_sql = self.INSERT_TABLE_FLAVOR_ID_MAPPING
        cursor.execute(exe_sql, (cascading_flavor_id, cascaded_flavor_id))
        self.commit()

    def delete_flavor_id_mapping(self, cascading_flavor_id):
        cursor = self.connect().cursor()
        exe_sql = "DELETE FROM flavor_id_mapping WHERE cascading_flavor_id = ?"
        data = [cascading_flavor_id]
        cursor.execute(exe_sql, data)
        self.commit()

    def get_cascaded_flavor_id(self, cascading_flavor_id):
        cursor = self.connect().cursor()
        cursor.execute("SELECT cascaded_flavor_id FROM flavor_id_mapping "
                       "WHERE cascading_flavor_id = '%s'" % cascading_flavor_id)
        row = cursor.fetchone()
        if row:
            return str(row[0])

        return None

    def add_volume_mapping(self, cascading_volume_id, cascaded_volume_id,
                           cascaded_backup_id=None, cascaded_image_id=None):
        cursor = self.connect().cursor()
        exe_sql = self.INSERT_VOLUME_MAPPING
        cursor.execute(exe_sql, (cascading_volume_id, cascaded_volume_id, cascaded_backup_id, cascaded_image_id))
        self.commit()

    def get_cascaded_volume_id(self, cascading_volume_id):
        cursor = self.connect().cursor()
        cursor.execute("SELECT cascaded_volume_id FROM volume_mapping "
                       "WHERE cascading_volume_id = '%s'"
                                 % cascading_volume_id)
        row = cursor.fetchone()
        if row:
            return str(row[0])

        return None

    def update_cascaded_backup_in_volume_mapping(self, cascading_volume_id, cascaded_backup_id):
        cursor = self.connect().cursor()
        cursor.execute("UPDATE volume_mapping SET cascading_volume_id='%s' WHERE cascaded_volume_id='%s'" %
                       (cascaded_backup_id, cascading_volume_id))
        self.commit()

    def update_cascaded_image_in_volume_mapping(self, cascading_volume_id, cascaded_image_id):
        cursor = self.connect().cursor()
        cursor.execute("UPDATE volume_mapping SET cascading_volume_id='%s' WHERE cascaded_volume_id='%s'" %
                       (cascaded_image_id, cascading_volume_id))
        self.commit()

    def update_cascaded_volume_in_volume_mapping(self, cascading_volume_id, cascaded_volume_id):
        cursor = self.connect().cursor()
        cursor.execute("UPDATE volume_mapping SET cascaded_volume_id='%s' WHERE cascading_volume_id='%s'" %
                       (cascaded_volume_id, cascading_volume_id))
        self.commit()

    def get_cascaded_backup(self, cascading_volume_id):
        cursor = self.connect().cursor()
        cursor.execute("SELECT cascaded_backup_id FROM volume_mapping "
                       "WHERE cascading_volume_id = '%s'"
                                 % cascading_volume_id)
        row = cursor.fetchone()
        if row:
            return str(row[0])

        return None

    def get_cascaded_backup_image(self, cascading_volume_id):
        cursor = self.connect().cursor()
        cursor.execute("SELECT cascaded_image_id FROM volume_mapping "
                       "WHERE cascading_volume_id = '%s'"
                                 % cascading_volume_id)
        row = cursor.fetchone()
        if row:
            return str(row[0])

        return None

    def delete_volume_mapping(self, cascading_volume_id):
        cursor = self.connect().cursor()
        exe_sql = "DELETE FROM volume_mapping WHERE cascading_volume_id = ?"
        data = [cascading_volume_id]
        cursor.execute(exe_sql, data)
        self.commit()

    def drop_table(self, table_name):
        cursor = self.connect().cursor()
        cursor.execute('drop table if exists %s' % table_name)
        self.commit()

    def create_tables(self, create_table_sql_list):
        """

        :param table_name_list: list of table names.
        :return:
        """
        cursor = self.connect().cursor()
        for create_table_sql in create_table_sql_list:
            cursor.execute(create_table_sql)
        self.commit()

    def drop_all_tables(self):
        self.drop_table_server_id_mapping()
        self.drop_table_server_id_name_mapping()
        self.drop_table_image_id_mapping()
        self.drop_table_flavor_id_mapping()
        self.drop_table_volume_mapping()

    def create_table(self, create_table_sql):
        self.create_tables([create_table_sql])

    def drop_table_server_id_mapping(self):
        self.drop_table('server_id_mapping')

    def drop_table_server_id_name_mapping(self):
        self.drop_table('server_id_name_mapping')

    def drop_table_image_id_mapping(self):
        self.drop_table('image_id_mapping')

    def drop_table_flavor_id_mapping(self):
        self.drop_table('flavor_id_mapping')

    def drop_table_volume_mapping(self):
        self.drop_table('volume_mapping')

    def create_table_image_id_mapping(self):
        if not self.is_table_exist('image_id_mapping'):
            self.create_table(self.CREATE_TABLE_IMAGE_ID_MAPPING)

    def create_table_server_id_mapping(self):
        if not self.is_table_exist('server_id_mapping'):
            self.create_table(self.CREATE_TABLE_SERVER_ID_MAPPING)

    def create_table_server_id_name_mapping(self):
        if not self.is_table_exist('server_id_name_mapping'):
            self.create_table(self.CREATE_TABLE_SERVER_ID_NAME_MAPPING)

    def create_table_flavor_id_mapping(self):
        if not self.is_table_exist('flavor_id_mapping'):
            self.create_table(self.CREATE_TABLE_FLAVOR_ID_MAPPING)

    def create_table_volume_mapping(self):
        if not self.is_table_exist('volume_mapping'):
            self.create_table(self.CREATE_TABLE_VOLUME_MAPPING)

    def is_table_exist(self, table_name):
        cursor = self.connect().cursor()
        sql = "SELECT name FROM sqlite_master WHERE type='table' AND name='%s'" % table_name

        cursor.execute(sql)
        row = cursor.fetchone()
        if row:
            return True

        return False


if __name__ == '__main__':
    database_manager = DatabaseManager()
    if len(sys.argv) <= 1:
        database_manager.close()
        exit(0)
    mode = sys.argv[1]

    if mode == 'init_db':
        print('Start to create database for Database Manager >>>>>>')
        database_manager.init_database()
        print('End to create database for Database Manager >>>>>>')
    elif mode == 'drop_db':
        print('Start to drop database for Database Manager >>>>>>')
        database_manager.drop_all_tables()
        print('Finish to drop database for Database Manager >>>>>>')
    elif mode == 'add_image_mapping':
        if len(sys.argv) == 4:
            cascading_image_id = sys.argv[2]
            cascaded_image_id = sys.argv[3]
            database_manager.add_image_id_mapping(cascading_image_id, cascaded_image_id)
    elif mode == 'add_flavor_mapping':
        if len(sys.argv) == 4:
            cascading_flavor_id = sys.argv[2]
            cascaded_flavor_id = sys.argv[3]
            database_manager.add_flavor_id_mapping(cascading_flavor_id, cascaded_flavor_id)
    elif mode == 'get_cascaded_image':
        if len(sys.argv) == 3:
            cascading_image_id = sys.argv[2]
            cascaded_image_id = database_manager.get_cascaded_image_id(cascading_image_id)
            print('cascaded image id: %s' % cascaded_image_id)
    elif mode == 'get_cascaded_flavor':
        if len(sys.argv) == 3:
            cascading_flavor_id = sys.argv[2]
            cascaded_flavor_id = database_manager.get_cascaded_flavor_id(cascading_flavor_id)
            print('cascaded flavor id: %s' % cascaded_flavor_id)

    database_manager.close()

