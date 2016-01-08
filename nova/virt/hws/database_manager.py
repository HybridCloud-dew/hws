__author__ = 'Administrator'

import sqlite3
import sys
import os
from nova.openstack.common import log as logging
LOG = logging.getLogger(__name__)


class DatabaseManager(object):
    conn = None

    def __init__(self):
        self.HWS_GATEWAY_NOVA_DB = 'hws_gateway_nova.db'
        self.DB_STORE_PATH = "/home/sqlite_db"

        self.CREATE_TABLE_SERVER_ID_MAPPING = \
            '''CREATE TABLE server_id_mapping(cascading_server_id text, cascaded_server_id text)'''
        self.INSERT_SERVER_ID_MAPPING = \
            '''INSERT INTO server_id_mapping(cascading_server_id, cascaded_server_id) VALUES (?,?)'''

        self.CREATE_TABLE_SERVER_ID_NAME_MAPPING = \
            '''CREATE TABLE server_id_name_mapping(cascading_server_id text, cascaded_server_name text)'''

        self.INSERT_SERVER_ID_NAME_MAPPING = \
            '''INSERT INTO server_id_name_mapping(cascading_server_id, cascaded_server_name) VALUES (?,?)'''

        db_full_name = self.get_hws_gateway_db_full_name()
        if not os.path.isfile(db_full_name):
            self.init_database()
            LOG.info('SQLite database has been created.')

    def get_current_dir(self):
        return os.path.split(os.path.realpath(__file__))[0]

    def get_hws_gateway_db_full_name(self):
        full_name = os.path.join(self.DB_STORE_PATH, self.HWS_GATEWAY_NOVA_DB)
        LOG.info('SQLite database path: %s' % full_name)
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
        cursor = self.connect().cursor()
        cursor.execute(self.CREATE_TABLE_SERVER_ID_MAPPING)
        cursor.execute(self.CREATE_TABLE_SERVER_ID_NAME_MAPPING)
        self.commit()

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

    def drop_table(self, table_name):
        cursor = self.connect().cursor()
        cursor.execute('drop table if exists %s' %s)
        self.commit()

    def drop_table_server_id_mapping(self):
        self.drop_table('server_id_mapping')

    def drop_table_server_id_name_mapping(self):
        self.drop_table('server_id_name_mapping')

if __name__ == '__main__':
    database_manager = DatabaseManager()
    if len(sys.argv) <= 1:
        cascading_server_id = "test1_1"
        # database_manager.add_server_id_mapping("cascading_01", "cascaded_01")

        cascaded_server_id = database_manager.get_cascaded_server_id(cascading_server_id)
        print cascaded_server_id
        database_manager.delete_server_id_by_cascading_id(cascading_server_id)
        cascaded_server_id = database_manager.get_cascaded_server_id(cascading_server_id)
        print cascaded_server_id
        database_manager.close()
        exit(0)
    mode = sys.argv[1]

    if mode == 'drop_db':
        print('Start to drop database for Database Manager >>>>>>')
        database_manager.drop_table_server_id_mapping()
        database_manager.close()
        print('Finish to drop database for Database Manager >>>>>>')

    database_manager.close()


