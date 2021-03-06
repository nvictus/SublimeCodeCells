from __future__ import print_function
from os.path import dirname, abspath
import sublime, sublime_plugin
import subprocess
import os.path
import sys
import re

runner = os.path.join(dirname(abspath(__file__)), 'bin', 'run_cell.py')

def extract_cell(view, cursor):
    tags = view.find_by_selector("punctuation.section.cell.begin")
    starts = [0] + [tag.a for tag in tags] + [view.size()]
    region = None
    for begin, end in zip(starts[:-1], starts[1:]):
        if begin <= cursor < end:
            region = sublime.Region(begin, end)
            next = end
            break
    if not region:
        if cursor == end:
            region = sublime.Region(begin, end)
            next = end
        else:
            raise ValueError(
                "Position (%d,%d) could not be matched to a cell." 
                % view.rowcol(cursor))
    return region, next

class EvalCellCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view
        selections = view.sel()
        
        venv_path = view.settings().get('virtual_env_path')
        if venv_path:
            cmd = [os.path.join(venv_path, 'bin', 'python'), runner]  
        else:
            cmd = ['/usr/bin/env', 'python', runner]

        for selection in selections:
            pos = selection.begin()
            cell, next_pos = extract_cell(view, pos)
            code = view.substr(cell).strip('\n')
            head, code = code.split('\n', 1)    

            print("sending %s" % head)
            # Call the system Python to connect to IPython kernel
            p = subprocess.Popen(
                    cmd + [code],
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE)
            
            # Response
            if p.stdout:
                for line in p.stdout:
                    print(line.decode('utf-8').rstrip())
                    p.stdout.flush()
                print()

            if p.stderr:
                # strip the ansi color codes from the ultraTB traceback
                regex = re.compile('\x1b\[[0-9;]*m', re.UNICODE)
                for line in p.stderr: 
                    print(regex.sub('', line.decode('utf-8').rstrip()))
                    p.stderr.flush()
                print()

        selections.clear()
        selections.add(sublime.Region(next_pos,next_pos))

class ToggleFoldCellCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view
        selections = view.sel()
        for selection in selections:
            region = selection
            if region.empty():
                region = sublime.Region(selection.a-1, selection.a+1)

            unfolded = view.unfold(region)
            if len(unfolded) == 0: #already unfolded
                pos = selection.begin()
                cell, next_pos = extract_cell(view, pos)
                lines = view.lines(cell)
                region_to_fold = sublime.Region(lines[1].a-1, lines[-1].b)
                view.fold(region_to_fold)

class SetVirtualenvCommand(sublime_plugin.TextCommand):
    def set_venv_path(self, venv):
        settings = self.view.settings()
        settings.set('virtual_env_path', os.path.expanduser(venv))   
         
    def run(self, edit):
        settings = self.view.settings()
        text = settings.get('virtual_env_path') or os.path.expanduser('~/.virtualenvs/')
        self.view.window().show_input_panel(
            'Path to virtualenv', text, self.set_venv_path, None, None)

