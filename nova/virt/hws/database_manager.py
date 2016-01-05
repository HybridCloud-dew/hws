__author__ = 'Administrator'

import sqlite3
import sys
import traceback
import os
from nova.openstack.common import log as logging
LOG = logging.getLogger(__name__)


class DatabaseManager(object):
    conn = None

    def __init__(self):
        self.HWS_GATEWAY_DB = 'hws_gateway.db'
        self.DB_STORE_PATH = "/home/sqlite_db"

        self.CREATE_TABLE_SERVER_ID_MAPPING = \
            '''CREATE TABLE server_id_mapping(cascading_server_id text, cascaded_server_id text)'''
        self.INSERT_SERVER_ID_MAPPING = \
            '''INSERT INTO server_id_mapping(cascading_server_id, cascaded_server_id) VALUES (?,?)'''

        db_full_name = self.get_hws_gateway_db_full_name()
        if not os.path.isfile(db_full_name):
            self.init_database()
            LOG.info('SQLite database has been created.')

    def get_current_dir(self):
        return os.path.split(os.path.realpath(__file__))[0]

    def get_hws_gateway_db_full_name(self):
        full_name = os.path.join(self.DB_STORE_PATH, self.HWS_GATEWAY_DB)
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
        self.commit()

    def add_server_id_mapping(self, cascading_server_id, cascaded_server_id):
        cursor = self.connect().cursor()
        exe_sql = self.INSERT_SERVER_ID_MAPPING
        cursor.execute(exe_sql, (cascading_server_id, cascaded_server_id))
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

    def drop_table(self, table_name):
        cursor = self.connect().cursor()
        cursor.execute('drop table if exists %s' %s)
        self.commit()

    def drop_table_server_id_mapping(self):
        self.drop_table('server_id_mapping')

if __name__ == '__main__':
    database_manager = DatabaseManager()
    if len(sys.argv) <= 1:
        # database_manager.add_server_id_mapping("cascading_01", "cascaded_01")

        cascaded_server_id = database_manager.get_cascaded_server_id("test1_1")
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


