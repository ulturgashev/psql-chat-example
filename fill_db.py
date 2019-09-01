import argparse
import asyncio
import asyncpg

import datetime
import pytz
import random
import string
import uuid


VOWELS = "aeiou"
CONSONANTS = "".join(set(string.ascii_lowercase) - set(VOWELS))


def generate_word(length = None):
    if length is None:
        length = random.randint(6, 10)
    word = ""
    for i in range(length):
        if i % 2 == 0:
            word += random.choice(CONSONANTS)
        else:
            word += random.choice(VOWELS)
    return word


def get_dsn():
    return 'postgres://postgres:example@localhost:5432/postgres'


def max_available_dialogs(user_count):
    k = 2
    n = user_count

    if 0 <= k <= n:
        ntok = 1
        ktok = 1
        for t in range(1, min(k, n - k) + 1):
            ntok *= n
            ktok *= t
            n -= 1
        return ntok // ktok
    else:
        return 0


def gen_dialogs(count, users):
    if len(users) > max_available_dialogs(count):
        return []

    def is_unique_pair(lhs, rhs, d):
        return lhs != rhs and rhs not in d.get(lhs, []) and lhs not in d.get(rhs, [])

    def find_unique(key, d, l):
        for entry in l:
            values = d.get(key, [])
            if entry not in values and entry != key:
                return entry

    i = 0
    user_ids = [entry[0] for entry in users]
    results = []
    unique_counter = {}
    while i < count:
        first_user = random.choice(user_ids)
        second_user = random.choice(user_ids)

        if not is_unique_pair(first_user, second_user, unique_counter):
            second_user = find_unique(first_user, unique_counter, user_ids)
            if second_user is None:
                continue

        results.append((
            uuid.uuid4().hex,
            datetime.datetime.utcnow(),
            first_user,
            second_user,
        ))

        print('users: ',first_user, second_user)
        if first_user not in unique_counter:
            unique_counter[first_user] = []
        if second_user not in unique_counter:
            unique_counter[second_user] = []
        unique_counter[first_user].append(second_user)
        unique_counter[second_user].append(first_user)
        i = i + 1

    return results


def gen_users(count):
    return [
        (
            random.getrandbits(40),
            datetime.datetime.utcnow(),
            generate_word(),
            generate_word(),
            'en'
        ) for i in range(count)
    ]


def gen_messages(dialogs, users, count):
    results = []
    now = datetime.datetime.utcnow()
    timestamp = int(now.timestamp())
    counter = {}
    middle = count / 2
    for i in range(count):
        dialog_id = random.choice(dialogs)[0]
        if dialog_id in counter:
            counter[dialog_id] += 1
        else:
            counter[dialog_id] = 0

        results.append((
            uuid.uuid4().hex,
            dialog_id,
            counter[dialog_id],
            random.choice(users)[0],
            datetime.datetime.utcfromtimestamp(
                timestamp - random.getrandbits(20)
            ),
            True if i > middle else False,
            generate_word(10),
        ))

    return results


# NOTE: It is unused right now
def gen_counters(chats):
    return [
        (uuid.uuid4().hex, chat[0], 0) for chat in chats
    ]


def build_query(table_name, values):
    return '''INSERT INTO {} VALUES {}'''.format(
        table_name, ','.join(values)
    )


async def fill_dialogs(conn, dialogs):
    values = [
        "('{}', '{}', '{}', '{}')".format(
            dialog[0], dialog[1], dialog[2], dialog[3]
        )
        for dialog in dialogs
    ]
    await conn.execute(build_query('chat.dialogs', values))


async def fill_users(conn, users):
    values = [
        "({}, '{}', '{}', '{}', '{}')".format(
            user[0], user[1], user[2], user[3], user[4]
        )
        for user in users
    ]
    await conn.execute(build_query('chat.users', values))


# NOTE: It is unused right now
async def fill_counters(conn, counters):
    values = [
        "('{}', {})".format(counter[0], counter[1])
        for counter in counters
    ]
    query = '''INSERT INTO chat.counters (chat_id, count) VALUES {}'''.format(
        values
    )
    await conn.execute(query)


async def fill_messages(conn, messages):
    values = [
        "('{}', '{}', {}, '{}', '{}'::timestamptz, {})".format(
            message[0],
            message[1],
            message[2],
            message[3],
            message[4],
            message[5]
        )
        for message in messages
    ]
    # print(build_query('chat.messages', values))
    await conn.execute(build_query('chat.messages', values))


async def drop_schema(conn):
    await conn.execute('''DROP SCHEMA IF EXISTS chat CASCADE''')


async def create_table(conn):
    with open('schemes/create_table.sql', 'r') as fopen:
        query = fopen.read()
    await conn.execute(query)


def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--chats_count',
        type=int,
        default=20,
        help=''
    )
    parser.add_argument(
        '--users_count',
        type=int,
        default=10,
        help=''
    )
    parser.add_argument(
        '--messages_count',
        type=int,
        default=100,
        help=''
    )
    parser.add_argument(
        '--drop',
        type=bool,
        default=True,
        help='Drop all tables before initialize'
    )
    return parser.parse_args()


async def fill_tables(conn, args):
    print('start prepearing data')
    users = gen_users(args.users_count)
    dialogs = gen_dialogs(args.chats_count, users)
    counters = gen_counters(dialogs)
    messages = gen_messages(dialogs, users, args.messages_count)
    print('finish prepearing data')

    await drop_schema(conn)
    print('schema was dropped')
    await create_table(conn)
    print('tables was created')
    await fill_users(conn, users)
    print('filled users')
    await fill_dialogs(conn, dialogs)
    print('filled dialogs')
    await fill_messages(conn, messages)
    print('filled messages')
    print('done')


async def main():
    args = _parse_args()

    conn = await asyncpg.connect(get_dsn())
    await fill_tables(conn, args)
    await conn.close()


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
