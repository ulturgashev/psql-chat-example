import argparse
import asyncio
import asyncpg

import datetime
import pytz
import random
import string
import uuid


SINGLE_CHAT_MEMBER_COUNT = 2
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


def gen_dialogs(count):
    return [
        (uuid.uuid4().hex, generate_word(), datetime.datetime.utcnow())
        for i in range(count)
    ]


def gen_participants(dialogs, users, type='single'):
    def make_dialog_touple(user_id, dialog_id, type):
        return (user_id, dialog_id, datetime.datetime.utcnow(), type)

    def is_unique_pair(user_ids, users_dialogs):
        for user_id in user_ids:
            if user_id not in users_dialogs:
                return True

        user_id_list = list(user_ids)
        l_dialogs = users_dialogs[user_id_list[0]]
        r_dialogs = users_dialogs[user_id_list[1]]
        intersections = l_dialogs & r_dialogs
        if len(intersections):
            return False
        return True

    def get_unique_users(users, users_dialogs, count):
        user_ids = set()
        while len(user_ids) < count:
            user_ids.add(random.choice(users)[0])

        if count == SINGLE_CHAT_MEMBER_COUNT:
            if not is_unique_pair(user_ids, users_dialogs):
                return get_unique_users(users, users_dialogs, count)

        return user_ids

    count = (
        SINGLE_CHAT_MEMBER_COUNT
        if type == 'single' else random.randint(3, len(users))
    )
    results = []
    users_dialogs = {}
    for dialog in dialogs:
        dialog_id = dialog[0]
        unique_user_ids = get_unique_users(
            users, users_dialogs, count
        )
        for user_id in unique_user_ids:
            if user_id not in users_dialogs:
                users_dialogs[user_id] = set()
            users_dialogs[user_id].add(dialog_id)
            results.append(make_dialog_touple(user_id, dialog_id, type))

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
    unread_count = count - count / 5
    for i in range(count):
        results.append((
            uuid.uuid4().hex,
            random.choice(dialogs)[0],
            random.choice(users)[0],
            datetime.datetime.utcfromtimestamp(
                timestamp - random.getrandbits(20)
            ),
            True if i > unread_count else False,
            generate_word(10),
        ))

    return results


def build_query(table_name, values):
    return '''INSERT INTO {} VALUES {}'''.format(
        table_name, ','.join(values)
    )


async def fill_dialogs(conn, dialogs):
    values = [
        "('{}', '{}', '{}')".format(
            dialog[0], dialog[1], dialog[2]
        )
        for dialog in dialogs
    ]
    await conn.execute(build_query('chat.dialogs', values))


async def fill_participants(conn, participants):
    values = [
        "('{}', '{}', '{}', '{}')".format(
            participant[0], participant[1], participant[2], participant[3]
        )
        for participant in  participants
    ]
    await conn.execute(build_query('chat.participants', values))


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


async def fill_messages(conn, dialogs, users, count):
    BATCH_SIZE = 20000
    counter = 0
    while counter < count:
        messages = gen_messages(dialogs, users, BATCH_SIZE)
        values = [
            "('{}', '{}', {}, '{}'::timestamptz, '{}', '{}')".format(
                message[0],
                message[1],
                message[2],
                message[3],
                message[4],
                message[5]
            )
            for message in messages
        ]
        await conn.execute(
            build_query('chat.messages', values)
        )
        counter = counter + BATCH_SIZE


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
        default=100,
        help=''
    )
    parser.add_argument(
        '--users_count',
        type=int,
        default=100,
        help=''
    )
    parser.add_argument(
        '--messages_count',
        type=int,
        default=1000000,
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
    dialogs = gen_dialogs(args.chats_count)
    participants = gen_participants(dialogs, users)

    await drop_schema(conn)
    print('schema was dropped')
    await create_table(conn)
    print('tables was created')
    await fill_users(conn, users)
    print('filled users')
    await fill_dialogs(conn, dialogs)
    print('filled dialogs')
    await fill_participants(conn, participants)
    print('filled participants')
    await fill_messages(conn, dialogs, users, args.messages_count)
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
