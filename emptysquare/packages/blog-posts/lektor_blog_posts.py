# -*- coding: utf-8 -*-
import posixpath

from jinja2 import Undefined
from lektor.build_programs import BuildProgram
from lektor.context import get_ctx
from lektor.db import F
from lektor.pluginsystem import Plugin
from lektor.sourceobj import VirtualSourceObject
from lektor.types import Type
import markdown  # This is "Python Markdown": pip install markdown
from werkzeug.utils import cached_property


def blog_posts():
    ctx = get_ctx()
    return ctx.record.pagination.items.filter(F._model == 'blog-post' and
                                              F.type == 'post')


class HTML(object):
    def __init__(self, html):
        self.html = html

    def __html__(self):
        return self.html


class MotorBlogMarkdownType(Type):
    def value_from_raw(self, raw):
        return HTML(markdown.markdown(raw.value or u'', extensions=[
            'codehilite(linenums=False,noclasses=True)',
            'fenced_code',
            'extra',
            'toc']))


class TagPage(VirtualSourceObject):
    def __init__(self, parent, plugin, tag):
        if not tag:
            raise ValueError("invalid tag %r" % tag)
        VirtualSourceObject.__init__(self, parent)
        self.plugin = plugin
        self.tag = tag

    @cached_property
    def items(self):
        if self.tag is None:
            return []
        return list(self._iter_items())

    def _iter_items(self):
        model_id = self.plugin.get_tag_model()
        for item in self.parent.children:
            if item.datamodel.id != model_id:
                continue

            tags = self.plugin.get_tags(item)
            if tags and self.tag in tags:
                yield item

    @property
    def path(self):
        return self._get_path(self.parent.path)

    @property
    def url_path(self):
        return self._get_path(self.parent.url_path)

    def _get_path(self, root):
        pieces = []
        root = root.strip('/')
        if root:
            pieces.append(root)

        pieces.append(self.plugin.get_tag_path_root())
        if self.tag is not None:
            pieces.append(self.tag)

        return '/%s/' % '/'.join(pieces)

    @property
    def template_name(self):
        return self.plugin.get_template_name()


class TagPageBuildProgram(BuildProgram):
    def produce_artifacts(self):
        self.declare_artifact(
            posixpath.join(self.source.url_path, 'index.html'),
            sources=list(self.source.iter_source_filenames()))

    def build_artifact(self, artifact):
        artifact.render_template_into(self.source.template_name,
                                      this=self.source)


def get_path_segments(str):
    pieces = str.split('/')
    if pieces == ['']:
        return []
    return pieces


class BlogPostsPlugin(Plugin):
    name = u'blog-posts'
    description = u'Lektor customization just for emptysqua.re.'

    def on_setup_env(self, **extra):
        self.env.types['motor_blog_markdown'] = MotorBlogMarkdownType
        self.env.jinja_env.globals['blog_posts'] = blog_posts
        self.env.add_build_program(TagPage, TagPageBuildProgram)

        blog_path = self.get_blog_path()

        @self.env.urlresolver
        def tag_resolver(node, url_path):
            # url_path is a list of segments.
            if node.path != blog_path or not url_path:
                return

            blog = node
            tag_path_root = get_path_segments(self.get_tag_path_root())
            if url_path[:len(tag_path_root)] != tag_path_root:
                return
            
            tag_segments = url_path[len(tag_path_root):]
            if len(tag_segments) != 1:
                return
            
            tag = tag_segments[0]
            page = TagPage(blog, self, tag)
            if page.items:
                return page

        @self.env.generator
        def generate_tag_pages(source):
            if source.path != blog_path:
                return

            blog = source
            for tag in self.get_all_tags(blog):
                yield TagPage(blog, self, tag)

    def get_blog_path(self):
        return self.get_config().get('blog_path', '/blog')

    def get_tag_path_root(self):
        return self.get_config().get('tag_path_root', 'tag').strip('/')

    def get_tag_model(self):
        return self.get_config().get('tag_model', 'blog-post')

    def get_tags(self, record):
        return record[self.get_tag_field_name()]

    def get_tag_field_name(self):
        return self.get_config().get('tag_field', 'tags')

    def get_template_name(self):
        return self.get_config().get('template', 'tag.html')

    def get_all_tags(self, blog):
        tag_field = self.get_tag_field_name()
        model_id = self.get_tag_model()
        tags = set()
        for item in blog.children:
            if item.datamodel.id != model_id:
                continue
            if tag_field not in item:
                continue
            item_tags = item[tag_field]
            if isinstance(item_tags, (list, tuple)):
                tags |= set(item_tags)
            elif not isinstance(item_tags, Undefined):
                tags.add(item_tags)

        return sorted(tags)
