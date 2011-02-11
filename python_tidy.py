'''
Wrapper for PythonTidy to tidy either the current line or all selections.
For using add something like this to your user definable key bindings file:
{ "keys": ["ctrl+alt+shift+t"], "command": "python_tidy" }

@author: Oktay Acikalin <ok@ryotic.de>

@license: MIT (http://www.opensource.org/licenses/mit-license.php)

@since: 2011-02-06
'''

import re
import StringIO
import textwrap

import sublime
import sublime_plugin

try:
    import PythonTidy
except ImportError:
    msg = 'PythonTidy (e.g. ver 1.20) not found. Please install it first.'
    sublime.status_message(msg)
    print msg


# Set this to True if you want to see what is being processed.
DEBUG = False


class PythonTidyCommand(sublime_plugin.TextCommand):
    '''
    A text command to tidy either the current line or all selections.
    '''

    def _debug(self, *args):
        if DEBUG:
            print ' '.join([str(item) for item in args])

    def run(self, edit):
        '''
        Gathers all selections, runs it thru PythonTidy and replaces the
        selections.

        @type  edit: sublime.Edit
        @param edit: Object used for replacement actions.

        @return: None
        '''
        regions = []
        PythonTidy.SHEBANG = ''
        PythonTidy.CODING_SPEC = ''
        PythonTidy.COL_LIMIT = 78
        PythonTidy.KEEP_UNASSIGNED_CONSTANTS = True
        PythonTidy.ADD_BLANK_LINES_AROUND_COMMENTS = False
        for region in self.view.sel():
            self._debug('region =', region, type(region))
            line = self.view.line(region)
            self._debug('line =', line, type(line))
            line_begin = self.view.rowcol(line.begin())[0] + 1
            line_end = self.view.rowcol(line.end())[0] + 1
            self._debug('line_begin =', line_begin)
            self._debug('line_end =', line_end)
            line_contents = self.view.substr(line)

            stripped = 0
            # remove last row from line_contents
            last_row = line_contents[line_contents.rfind('\n'):]
            self._debug('last_row =', last_row.__repr__())
            if len(last_row) and last_row[-1] == '\n':
                if len(last_row.strip()) and '\n' in line_contents:
                    self._debug('strip', ord(last_row[-1]), last_row[-1])
                    stripped = line_contents.rfind('\n')
                    line_contents = line_contents[:stripped]

            whitespace = re.compile('^(\s*)')
            smallest_indent = None
            for line in line_contents.split('\n'):
                if len(line.strip()) == 0:
                    continue
                match = whitespace.match(line)
                indent = match.group(1)
                self._debug('match = "%s"' % indent)
                indent = indent.replace('\t', ' ' * 4)
                if smallest_indent is not None:
                    smallest_indent = min(len(indent), smallest_indent)
                else:
                    smallest_indent = len(indent)

            self._debug('=', line_contents.__repr__())
            line_contents = textwrap.dedent(line_contents)
            has_trailing_newline = len(line_contents) and \
                                   line_contents[-1] == '\n'
            self._debug('=', line_contents.__repr__())
            self._debug('smallest_indent =', smallest_indent)

            file_in = StringIO.StringIO()
            file_in.write(line_contents)
            file_in.seek(0)
            file_out = StringIO.StringIO()
            try:
                PythonTidy.tidy_up(file_in, file_out)
            except IndentationError:
                msg = 'Unexpected indent in region with line from %d to %d' % (
                    line_begin, line_end)
                print msg
                sublime.status_message(msg)
                continue
            except Exception, excp:
                msg = '%s within line from %d to %d' % (
                    excp, line_begin, line_end)
                print msg
                sublime.status_message(msg)
                continue
            file_out.seek(0)
            output = file_out.read().lstrip('\n')

            if smallest_indent is not None:
                self._debug('output =', output.__repr__())
                output = output.rstrip('\n')
                output = output.split('\n')
                for row, line in enumerate(output):
                    output[row] = ' ' * smallest_indent + line
                output = '\n'.join(output)
            
            if stripped:
                output += last_row

            self._debug('stripped =', stripped)
            if has_trailing_newline:
                output += '\n'

            self._debug('output =', output.__repr__())

            line = self.view.line(region)
            self.view.replace(edit, line, output)
            regions.append(line)
        
        self._debug('regions replaced:', regions)
        [self.view.sel().add(region) for region in regions]
