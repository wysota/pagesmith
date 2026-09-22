#!/usr/bin/env python3
"""Unit tests for URLManager (navigation and language-switcher URL generation)."""

import unittest

from pagesmith.url_manager import URLManager


def make_manager(permalink='posts/:slug'):
    languages = {
        'en': {'name': 'English', 'default': True},
        'pl': {'name': 'Polski', 'default': False},
    }
    config = {'build': {'permalink': permalink}}

    def section_pages():
        return ['about', 'services', 'contact']

    return URLManager(
        languages=languages,
        default_lang='en',
        config=config,
        get_section_page_names_fn=section_pages,
    )


def by_code(langs, code):
    return next(l for l in langs if l['code'] == code)


class TestPostsUrlPrefix(unittest.TestCase):

    def test_default_permalink(self):
        self.assertEqual(make_manager().get_posts_url_prefix(), 'posts')

    def test_custom_permalink(self):
        self.assertEqual(
            make_manager('blog/articles/:slug').get_posts_url_prefix(), 'blog/articles'
        )


class TestGetUrls(unittest.TestCase):

    def test_index_default_language(self):
        urls = make_manager().get_urls('index', 'en')
        self.assertEqual(urls['home'], './')
        self.assertEqual(urls['images'], './images')
        self.assertEqual(urls['tags'], './tags/')
        self.assertEqual(urls['about'], './sections/about.html')

    def test_section_default_language(self):
        urls = make_manager().get_urls('about', 'en')
        self.assertEqual(urls['home'], '../')
        self.assertEqual(urls['images'], '../images')
        self.assertEqual(urls['services'], './services.html')

    def test_section_non_default_language(self):
        urls = make_manager().get_urls('about', 'pl')
        self.assertEqual(urls['home'], '../')
        self.assertEqual(urls['images'], '../../images')
        self.assertEqual(urls['services'], './services.html')
        self.assertEqual(urls['tags'], '../tags/')

    def test_post_rendered_by_page_type_default_language(self):
        urls = make_manager().get_urls('my-post', 'en', page_type='post')
        self.assertEqual(urls['home'], '../')
        self.assertEqual(urls['posts'], './')
        self.assertEqual(urls['about'], '../sections/about.html')
        self.assertEqual(urls['tags'], '../tags/')

    def test_post_rendered_by_page_type_non_default_language(self):
        urls = make_manager().get_urls('my-post', 'pl', page_type='post')
        self.assertEqual(urls['home'], '../')
        self.assertEqual(urls['about'], '../sections/about.html')
        self.assertEqual(urls['tags'], '../tags/')

    def test_post_default_language(self):
        urls = make_manager().get_urls('post', 'en')
        self.assertEqual(urls['home'], '../')
        self.assertEqual(urls['posts'], './')
        self.assertEqual(urls['about'], '../sections/about.html')

    def test_child_page_default_language(self):
        urls = make_manager().get_urls('design_patterns/observer', 'en')
        self.assertEqual(urls['home'], '../../')
        self.assertEqual(urls['images'], '../../images')
        self.assertEqual(urls['about'], '../about.html')

    def test_child_page_non_default_language(self):
        urls = make_manager().get_urls('design_patterns/observer', 'pl')
        self.assertEqual(urls['home'], '../../')
        self.assertEqual(urls['images'], '../../../images')
        self.assertEqual(urls['tags'], '../../tags/')
        self.assertEqual(urls['about'], '../about.html')

    def test_nested_child_page_non_default_language(self):
        urls = make_manager().get_urls('design_patterns/strategy/visitor', 'pl')
        self.assertEqual(urls['home'], '../../../')
        self.assertEqual(urls['about'], '../../about.html')
        self.assertEqual(urls['tags'], '../../../tags/')


class TestGetLanguageUrls(unittest.TestCase):

    def test_index(self):
        langs = make_manager().get_language_urls('index', 'en')
        self.assertTrue(by_code(langs, 'en')['is_default'])
        self.assertFalse(by_code(langs, 'pl')['is_default'])
        self.assertEqual(by_code(langs, 'en')['page_url'], './')
        self.assertEqual(by_code(langs, 'pl')['page_url'], './pl/')
        self.assertEqual(by_code(langs, 'pl')['name'], 'Polski')

    def test_section_from_default_language(self):
        langs = make_manager().get_language_urls('about', 'en')
        self.assertEqual(by_code(langs, 'en')['page_url'], './about.html')
        self.assertEqual(by_code(langs, 'pl')['page_url'], '../pl/sections/about.html')

    def test_section_from_non_default_language(self):
        langs = make_manager().get_language_urls('about', 'pl')
        self.assertEqual(by_code(langs, 'pl')['page_url'], './about.html')
        self.assertEqual(by_code(langs, 'en')['page_url'], '../../sections/about.html')

    def test_post_from_default_language(self):
        langs = make_manager().get_language_urls('post', 'en', page_type='post')
        self.assertEqual(by_code(langs, 'en')['page_url'], './post.html')
        self.assertEqual(by_code(langs, 'pl')['page_url'], '../pl/posts/post.html')

    def test_child_page_from_default_language(self):
        langs = make_manager().get_language_urls('design_patterns/observer', 'en')
        self.assertEqual(by_code(langs, 'en')['page_url'], './observer.html')
        self.assertEqual(
            by_code(langs, 'pl')['page_url'],
            '../../pl/sections/design_patterns/observer.html',
        )

    def test_child_page_from_non_default_language(self):
        langs = make_manager().get_language_urls('design_patterns/observer', 'pl')
        self.assertEqual(by_code(langs, 'pl')['page_url'], './observer.html')
        self.assertEqual(
            by_code(langs, 'en')['page_url'],
            '../../../sections/design_patterns/observer.html',
        )

    def test_taxonomy_term_cross_language_links_to_index(self):
        # Term slugs differ per language (e.g. 'code' vs 'kod'); the language
        # switcher must link to the target language's taxonomy index instead of
        # a term slug that may not exist there.
        langs = make_manager().get_language_urls(
            'tags_term', 'en', 'taxonomy', 'code')
        self.assertEqual(by_code(langs, 'en')['page_url'], './')
        self.assertEqual(by_code(langs, 'pl')['page_url'], '../../pl/tags/')

    def test_taxonomy_term_from_non_default_language(self):
        langs = make_manager().get_language_urls(
            'tags_term', 'pl', 'taxonomy', 'kod')
        self.assertEqual(by_code(langs, 'pl')['page_url'], './')
        self.assertEqual(by_code(langs, 'en')['page_url'], '../../../tags/')


if __name__ == '__main__':
    unittest.main()