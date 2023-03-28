#!/usr/bin/env python3

import cmd
import argparse
from flightsql import FlightSQLClient
import json
from prompt_toolkit import PromptSession
from prompt_toolkit.lexers import PygmentsLexer
from pygments.lexers import SqlLexer
from influxdb_client import InfluxDBClient as InfluxDBCloudClient, WriteOptions

class IOXCLI(cmd.Cmd):
    intro = 'Welcome to my IOx CLI.\n'
    prompt = '(>) '

    def __init__(self):
        super().__init__()
        self._load_config()   

    def do_sql(self, arg):
        try: 
            query = self._flight_sql_client.execute(arg)
            reader = self._flight_sql_client.do_get(query.endpoints[0].ticket)
            table = reader.read_all()
            print(table.to_pandas().to_markdown())
        except Exception as e:
            print(e)

    def do_write(self, arg):
        print(arg, self._bucket_name)
        self._cloud_writer.write(bucket=self._bucket_name, record=arg)

    def do_exit(self, arg):
        'Exit the shell: exit'
        print('Exiting ...')
        return True

    def do_EOF(self, arg):
        'Exit the shell with Ctrl-D'
        return self.do_exit(arg)

    def precmd(self, line):
        if line.strip() == 'sql':
            while True:
                try:
                    self.prompt_session = PromptSession(lexer=PygmentsLexer(SqlLexer))
                    statement = self.prompt_session.prompt('(sql >) ')
                    if statement.strip().lower() == 'exit':
                        break
                    self.do_sql(statement)
                except KeyboardInterrupt:
                    print('Ctrl-D pressed, exiting SQL mode...')
                    break
            return ''
        if line.strip() == 'write':
            while True:
                try:
                    self.prompt_session = PromptSession(lexer=None)
                    statement = self.prompt_session.prompt('(write >) ')
                    if statement.strip().lower() == 'exit':
                        break
                    self.do_write(statement)
                except KeyboardInterrupt:
                    print('Ctrl-D pressed, exiting write mode...')
                    break
            return ''
        return line
    
    def _load_config(self):
        f = open('config.json')
        conf = json.loads(f.read())
        self._bucket_name = conf['namespace']
        self._flight_sql_client = FlightSQLClient(host=conf['host'],
                                                  token=conf['token'],
                                                  metadata={'bucket-name':self._bucket_name})
        
        client = InfluxDBCloudClient(conf['url'],
                                                 org=conf['org'],
                                                 token=conf['token'])
        self._cloud_writer = client.write_api(write_options=WriteOptions(batch_size=1))

class StoreRemainingInput(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, ' '.join(values))

def parse_args():
    parser = argparse.ArgumentParser(description='CLI application for Querying IOx with arguments and interactive mode.')
    subparsers = parser.add_subparsers(dest='command')

    sql_parser = subparsers.add_parser('sql', help='execute the given SQL query')
    sql_parser.add_argument('query', metavar='QUERY', nargs='*', action=StoreRemainingInput, help='the SQL query to execute')

    write_parser = subparsers.add_parser('write', help='write line protocol to InfluxDB')
    write_parser.add_argument('line_protocol', metavar='LINE PROTOCOL', nargs='*', action=StoreRemainingInput, help='the data to write')

    return parser.parse_args()

def main():
    args = parse_args()
    app = IOXCLI()

    if args.command == 'sql':
        app.do_sql(args.query)
    if args.command == 'write':
        app.do_write(args.line_protocol)
    if args.command is None:
        app.cmdloop()


if __name__ == '__main__':
    main()

