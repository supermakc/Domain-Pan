#!/usr/bin/env python

import sys, MySQLdb

db = {
    'username' : 'dc_user',
    'password' : 'password',
    'host' : 'localhost',
    'port' : 3306,
    'name' : 'domain_checker'}

tld_table = 'main_tld'
exclusion_table = 'main_excludeddomain'

tld_filename = 'tld_list.txt'
exclusion_filename = 'exclusion_domains.txt'

def main():
    tldf = open(tld_filename)
    tlds = [line.strip() for line in tldf if line[0] not in '/\n']
    tldf.close()

    exf = open(exclusion_filename)
    exl = [line.strip() for line in exf]
    exf.close()

    conn = MySQLdb.connect(user=db['username'], passwd=db['password'], host=db['host'], port=db['port'], db=db['name'])

    c = conn.cursor()

    tld_insertion_count = 0
    for tld in tlds:
        c.execute("""SELECT COUNT(*) FROM """+tld_table+""" WHERE domain = %s""", (tld,))
        if c.fetchone()[0] == 0:
            tld_insertion_count += 1
            c.execute("""INSERT INTO """+tld_table+""" (domain, is_recognized, is_api_registerable, type, description) VALUES(%s, 0, 0, '', NULL)""", (tld,))

    print 'TLDs: Inserted %d row(s) (out of %d TLDs)' % (tld_insertion_count, len(tlds))

    ex_insertion_count = 0
    for exd in exl:
        c.execute("""SELECT COUNT(*) FROM """+exclusion_table+""" WHERE domain = %s""", (exd,))
        if c.fetchone()[0] == 0:
            ex_insertion_count += 1
            c.execute("""INSERT INTO """+exclusion_table+""" (domain) VALUES(%s)""", (exd,))

    print 'Excluded domains: Inserted %d row(s) (out of %d listed domains)' % (ex_insertion_count, len(exl))

    conn.commit()

if __name__ == '__main__':
    main()

