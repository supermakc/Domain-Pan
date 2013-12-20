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
settings_table = 'main_adminsetting'

tld_filename = 'tld_list.txt'
exclusion_filename = 'exclusion_domains.txt'
settings_filename = 'clean_admin.txt'

def main():
    tldf = open(tld_filename)
    tlds = [line.strip() for line in tldf if line[0] not in '/\n']
    tldf.close()

    exf = open(exclusion_filename)
    exl = [line.strip() for line in exf]
    exf.close()

    sf = open(settings_filename)
    ss = [line.strip() for line in sf]
    sf.close()

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

    s_insertion_count = 0
    for s in ss:
        if len(s) == 0:
            continue
        vals = s.split('\t')
        try:
            key = vals[0]
            value = vals[1]
            valtype = vals[2]
            choices = None
            if len(vals) > 3:
                choices = vals[4]
            c.execute("""SELECT COUNT(*) FROM """+settings_table+""" WHERE `key` = %s""", (key,))
            if c.fetchone()[0] == 0:
                s_insertion_count += 1
                c.execute('''INSERT INTO '''+settings_table+''' (`key`, `value`, `type`, `choices`) VALUES(%s, %s, %s, %s)''', (key, value, valtype, choices))
        except IndexError as e:
            print 'Index error on line containing: %s' % s
            raise

    print 'Admin settings: Inserted %d row(s) (out of %d listed settings)' % (s_insertion_count, len(ss))

    conn.commit()

if __name__ == '__main__':
    main()

