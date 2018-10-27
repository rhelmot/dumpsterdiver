import gc
import traceback
import types
from pprint import pformat, pprint

from prompt_toolkit import prompt
from pygments.token import Token
from prompt_toolkit import print_formatted_text
from prompt_toolkit.formatted_text import PygmentsTokens
from prompt_toolkit.styles import Style

SEQUENCE_TYPES = [list, set, tuple]
MAPPING_TYPES = [dict]
MAGIC_HOLDER = [object()]
# the magic object is a unique object that we toss into gc.get_referrers to
# identify which object gc.get_referrer is returning which is actually the
# tuple of objects that are the args to gc.get_referrer. we hold it in a list
# so we can easily isolate which results need to be discarded by its inclusion.

def search(ty_filter):
    all_objects = [x for x in gc.get_objects() if ty_filter in repr(type(x))]
    mark_mine(all_objects)
    return _main(SearchGarbage(all_objects, 'Objects of type like %s' % ty_filter))

def start():
    hist = {}
    mark_mine(hist)
    for x in gc.get_objects():
        if type(x) in hist:
            hist[type(x)].append(x)
        else:
            hist[type(x)] = [x]
            mark_mine(hist[type(x)])
    return _main(SearchGarbage(hist, 'Histogram of types in memory', sort=lambda x: -len(hist[x])))

def _main(dumpster):
    try:
        dumpster.run()
        return None
    except ReturnException as e:
        return e.value
    except: # pylint: disable=bare-except
        #import ipdb, sys; ipdb.post_mortem(sys.exc_info()[2])
        traceback.print_exc()
        return None
    finally:
        clear_mine()
        gc.collect()

class ContinueException(Exception):
    pass
class BreakException(Exception):
    pass
class ReturnException(Exception):
    def __init__(self, v):
        super(ReturnException, self).__init__()
        self.value = v

mine = []

def mark_mine(obj):
    mine.append(obj)
    return obj

def is_mine(obj):
    if obj is mine or obj is MAGIC_HOLDER or obj is MAGIC_HOLDER[0]:
        return True
    if type(obj) is tuple and len(obj) > 0 and obj[-1] is MAGIC_HOLDER[0]:
        return True
    if type(obj) is types.FrameType and obj.f_code.co_filename.endswith('dive.py'):
        return True
    for m in mine:
        if m is obj:
            return True
    return False

def clear_mine():
    global mine
    mine = []

# styling stuff... why is this difficult
our_style = Style.from_dict({
    'prompt':             '#209000 bold',
    'pygments.number':   '#ff0000 bold',
    'pygments.error':    '#ffff00 bold',
    'pygments.key':      '#ff8888',
})

def print_tokens(tokens):
    print_formatted_text(PygmentsTokens(tokens), style=our_style)


class SearchGarbage(object): # pylint: disable=useless-object-inheritance
    def __init__(self, body, context, sort=None):
        self.idx_mode = type(body) in SEQUENCE_TYPES
        self.dict_mode = type(body) in MAPPING_TYPES
        self.dir_mode = not (self.idx_mode or self.dict_mode)
        self.last_offset = 0
        self.context = context

        if self.idx_mode:
            self.keys = None
            self.values = [x for x in body if not is_mine(x)]
        elif self.dict_mode:
            self.keys = sorted(body.keys(), key=sort)
            self.values = [body[x] for x in self.keys]
        else:
            self.keys = sorted((x for x in dir(body) if not isprop(body, x)), key=sort)
            self.values = [getattr(body, x) for x in self.keys]

        if self.keys is not None:
            mark_mine(self.keys)
        mark_mine(self.values)

    def list_items(self, offset=None, count=10):
        if offset is None:
            offset = self.last_offset
        for i in range(offset, min(offset + count, len(self.values))):
            if self.keys is not None:
                print_tokens([
                    (Token.Number, str(i)),
                    (Token, ': '),
                    (Token.Key, str(self.keys[i])),
                    (Token, ' => '),
                    (Token, meaningful_repr(self.values[i])),
                ])
            else:
                print_tokens([
                    (Token.Number, str(i)),
                    (Token, ': '),
                    (Token, meaningful_repr(self.values[i])),
                ])
        self.last_offset = offset + count

    def deeper(self, body, context, failure_advice):
        dumpster = SearchGarbage(body, context)
        if len(dumpster.values) > 0:
            dumpster.run()
            self.list_items(self.last_offset - 10)
        else:
            print_tokens([
                (Token.Error, 'There are no objects in this view!\n'),
                (Token, failure_advice),
            ])

    def validate_idx(self, idx):
        try:
            idx = int(idx)
        except ValueError:
            print('Not an index!')
            raise ContinueException()
        if idx < 0 or idx >= len(self.values):
            print('Not in range!')
            raise ContinueException()
        return idx

    def validate_key(self, key):
        if self.keys is None:
            return self.validate_idx(key)

        for i, maybe in enumerate(self.keys):
            if type(maybe) is str and maybe == key:
                return i
        if key.isdigit():
            return self.validate_idx(key)
        else:
            print('Not a key!')
            raise ContinueException()

    def run(self):
        self.last_offset = 0
        self.list_items()
        last_cmd = None

        while True:
            try:
                opt = prompt([('class:prompt', u'%s: ' % self.context)], style=our_style)
                if opt == '':
                    if last_cmd is None:
                        continue
                    opt = last_cmd
                else:
                    last_cmd = opt

                args = opt.split()
                if len(args) == 0 or not hasattr(self, 'cmd_' + args[0]):
                    print('Not a command. Type "help" for help.')
                else:
                    getattr(self, 'cmd_' + args[0])(*args[1:])

            except ContinueException:
                continue
            except BreakException:
                return True

    def cmd_help(self, *args): # pylint: disable=unused-argument,no-self-use
        print('help - show this message')
        print('list [n] - show 10 items from the list at index n')
        print('show n - show detail of item at index or key n')
        print('fullshow n - show ALL detail of item at index or key n')
        print('refs n - explore objects that refer to item at index or key n')
        print('down n - explore objects that the object at index or key n refers to')
        print('return n - pick item at index or key n')
        print('up - cancel selection')
        print('quit - abort everything')

    def cmd_list(self, *args):
        if len(args) == 1:
            idx = self.validate_idx(args[0])
        elif len(args) == 0:
            idx = None
        else:
            print('Syntax: list [n]')
            raise ContinueException()

        self.list_items(idx)

    def cmd_show(self, *args):
        if len(args) == 1:
            idx = self.validate_key(args[0])
        else:
            print('Syntax: show n')
            raise ContinueException()

        print(safe_repr(self.values[idx]))

    def cmd_fullshow(self, *args):
        if len(args) == 1:
            idx = self.validate_key(args[0])
        else:
            print('Syntax: fullshow n')
            raise ContinueException()

        pprint(self.values[idx])

    def cmd_refs(self, *args):
        if len(args) == 1:
            idx = self.validate_key(args[0])
        else:
            print('Syntax: refs n')
            raise ContinueException()

        self.deeper(gc.get_referrers(self.values[idx], MAGIC_HOLDER[0]), 'Objects referring to %s' % meaningful_repr(self.values[idx]), 'The object may be interned and have some refs hidden.')

    def cmd_down(self, *args):
        if len(args) == 1:
            idx = self.validate_key(args[0])
        else:
            print('Syntax: down n')
            raise ContinueException()

        self.deeper(self.values[idx], 'Objects referred to by %s' % meaningful_repr(self.values[idx]), 'Try looking at a non-empty object')

    def cmd_return(self, *args):
        if len(args) == 1:
            idx = self.validate_key(args[0])
        else:
            print('Syntax: return n')
            raise ContinueException()

        raise ReturnException(self.values[idx])

    def cmd_up(self, *args): # pylint: disable=unused-argument,no-self-use
        raise BreakException()

    def cmd_quit(self, *args): # pylint: disable=unused-argument,no-self-use
        raise ReturnException(None)

def meaningful_repr(x):
    if type(x) is dict:
        return 'dict with %d keys %s' % (len(x), shorten(x.keys()))
    elif type(x) is tuple:
        return 'tuple with %d items %s' % (len(x), shorten(x))
    elif type(x) is list:
        return 'list with %d items %s' % (len(x), shorten(x))
    elif type(x) is set:
        return 'set with %d items %s' % (len(x), shorten(x))
    else:
        r = repr(x)
        if '\n' in r:
            r = r.split('\n', 1)[0]
        if len(r) > 80:
            r = r[:80] + '...'
        return r

def shorten(seq):
    out = '['
    first = True
    for key in seq:
        if first:
            out += repr(key)
            first = False
        else:
            out += ', ' + repr(key)
        if len(out) > 50:
            return out[:50] + '...]'
    return out + ']'

def safe_repr(x):
    r = pformat(x)
    if len(r) > 10**4:
        r = r[:10**4] + '...'
    if len(r.splitlines()) > 50:
        r = '\n'.join(r.splitlines()[:50]) + '\n...'
    return r

def isprop(obj, attr):
    if attr not in dir(type(obj)):
        return False
    return type(getattr(type(obj), attr)) is property
