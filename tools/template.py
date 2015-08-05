# templates.py
# -*- coding: utf-8 -*-
#
# Copyright (c) 2015 Kevin Laeufer <kevin.laeufer@rwth-aachen.de>
#
# This file is part of ekiwi-scons-tools.
#
# ekiwi-scons-tools is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ekiwi-scons-tools is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ekiwi-scons-tools.  If not, see <http://www.gnu.org/licenses/>.

"""
# Template Tool
This code is inspired by the Template builder of the xpcc.io microcontroller
library.
This tool requires the python jinja2 template engine.
"""

import os, posixpath, re
import jinja2
import SCons


# Overwrite jinja2 Environment in order to enable relative paths
# since this runs locally that should not be a security concern
# Code from:
# http://stackoverflow.com/questions/8512677/how-to-include-a-template-with-relative-path-in-jinja2
class RelEnvironment(jinja2.Environment):
	""" Override join_path() to enable relative template paths. """
	def join_path(self, template, parent):
		# posixpath is needed instead of os.path, because jinja works
		# with posixpaths internally, even on windows
		d = posixpath.join(posixpath.dirname(parent), template)
		return posixpath.normpath(d)

def template_action(target, source, env):
	source_path = source[0].get_abspath()
	try:
		path = env['TEMPLATE_PATH']
	except KeyError:
		path = os.path.split(source_path)[0]
	filename = os.path.relpath(source_path, path)
	# try to convert filename to posix since jinja2 uses posix style paths
	# even on windows
	filename = filename.replace('\\', '/')
	jinja_env = RelEnvironment(loader=jinja2.FileSystemLoader(path))
	# Jinja2 Line Statements
	jinja_env.line_statement_prefix = '%%'
	jinja_env.line_comment_prefix = '%#'
	template = loader.get_template(filename)
	output = template.render(env['substitutions']).encode('utf-8')
	with open(target[0].path, 'w') as out_file:
		out_file.write(output)

def template_emitter(target, source, env):
	env.Depends(target, SCons.Node.Python.Value(env['substitutions']))
	return target, source

def template_string(target, source, env):
	return "Template: '%s' to '%s'" % (str(source[0]), str(target[0]))

includeExpression = re.compile(r"(\{%|%%)\s+(import|include)\s+'(?P<file>\S+)'")

def find_includes(file):
	""" Find include directives in an .in file """
	files = []
	for line in open(file).readlines():
		match = includeExpression.search(line)
		if match:
			filename = match.group('file')
			if not os.path.isabs(filename):
				filename = os.path.join(os.path.dirname(os.path.abspath(file)), filename)
			files.append(filename)
	return files

def in_include_scanner(node, env, path, arg=None):
	""" Generates the dependencies for the .in files """
	abspath, targetFilename = os.path.split(node.get_abspath())

	stack = [targetFilename]
	dependencies = [targetFilename]

	while stack:
		nextFile = stack.pop()
		files = find_includes(os.path.join(abspath, nextFile))
		for file in files:
			if file not in dependencies:
				stack.append(file)
				# env.Debug(".in include scanner found %s" % file)
		dependencies.extend(files)

	dependencies.remove(targetFilename)
	return dependencies

def generate(env):
	# Template Builder
	template_builder = SCons.Builder.Builder(
		action = env.Action(template_action, template_string),
		emitter = template_emitter,
		src_suffix = '.in',
		source_scanner =
			SCons.Script.Scanner(function=in_include_scanner, skeys=['.in']),
		single_source = True,
		target_factory = SCons.Node.FS.File,
		source_factory = SCons.Node.FS.File)
	env.Append(BUILDERS = { 'Template': template_builder })

def exists(env):
	return 1
