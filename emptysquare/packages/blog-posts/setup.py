from setuptools import setup

setup(
    name='lektor-blog-posts',
    version='0.1',
    author=u'A. Jesse Jiryu Davis',
    author_email='jesse@emptysquare.net',
    license='MIT',
    install_requires=['markdown>=2,<3', 'pygments>=2,<3'],
    py_modules=['lektor_blog_posts'],
    entry_points={
        'lektor.plugins': [
            'blog-posts = lektor_blog_posts:BlogPostsPlugin',
        ],
        'console_scripts': [
            'blog=lektor_blog_posts:cli',
        ]
    }
)
