from setuptools import setup

setup(
    name='lektor-blog-posts',
    version='0.1',
    author=u'A. Jesse Jiryu Davis',
    author_email='jesse@emptysquare.net',
    license='MIT',
    py_modules=['lektor_blog_posts'],
    entry_points={
        'lektor.plugins': [
            'blog-posts = lektor_blog_posts:BlogPostsPlugin',
        ]
    }
)
