import os
import re
import unittest
from html.parser import HTMLParser

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_PATH = os.path.join(BASE_DIR, "index.html")


class SiteHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.ids = set()
        self.images = []      # list of (src, alt)
        self.local_links = [] # list of hrefs
        self.anchor_targets = []  # list of '#id'
        self.meta_tags = []   # list of attrs dicts
        self.title = None
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        attr_dict = dict(attrs)
        self.tags.append((tag, attr_dict))

        if "id" in attr_dict:
            self.ids.add(attr_dict["id"])

        if tag == "title":
            self._in_title = True

        if tag == "meta":
            self.meta_tags.append(attr_dict)

        if tag == "img":
            src = attr_dict.get("src", "")
            alt = attr_dict.get("alt", "")
            self.images.append((src, alt))

        if tag in ("a", "link"):
            href = attr_dict.get("href", "")
            if href.startswith("#"):
                target = href[1:]
                if target:  # ignore bare '#'
                    self.anchor_targets.append(target)
            elif href and not href.startswith(("http://", "https://", "mailto:", "tel:", "javascript:")):
                self.local_links.append(href)

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title = data.strip()


class PortfolioSiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assertTrue(os.path.isfile(INDEX_PATH), f"index.html not found at {INDEX_PATH}")
        with open(INDEX_PATH, "r", encoding="utf-8") as f:
            cls.html_content = f.read()

        cls.parser = SiteHTMLParser()
        cls.parser.feed(cls.html_content)

    def test_document_title_and_metadata(self):
        """Page should have an informative title, viewport, and meta description."""
        self.assertIsNotNone(self.parser.title, "Missing <title> tag")
        self.assertIn("Alan Tan", self.parser.title)

        has_viewport = any(m.get("name") == "viewport" for m in self.parser.meta_tags)
        self.assertTrue(has_viewport, "Missing responsive viewport meta tag")

        has_desc = any(m.get("name") == "description" for m in self.parser.meta_tags)
        self.assertTrue(has_desc, "Missing meta description for SEO")

    def test_all_images_exist_and_have_alt_text(self):
        """All <img> tags must point to existing files and have non-empty alt text."""
        self.assertGreater(len(self.parser.images), 0, "No images found in index.html")
        for src, alt in self.parser.images:
            with self.subTest(image_src=src):
                self.assertTrue(bool(alt.strip()), f"Image '{src}' is missing an alt attribute")
                if not src.startswith(("http://", "https://", "data:")):
                    img_path = os.path.join(BASE_DIR, src)
                    self.assertTrue(os.path.isfile(img_path), f"Image file does not exist on disk: {img_path}")

    def test_local_links_exist(self):
        """Local file links (like vCard and icons) must exist on disk."""
        for href in self.parser.local_links:
            with self.subTest(local_link=href):
                file_path = os.path.join(BASE_DIR, href)
                self.assertTrue(os.path.isfile(file_path), f"Linked local file not found: {file_path}")

    def test_internal_anchor_navigation(self):
        """All '#target' navigation links must resolve to an existing element ID."""
        self.assertGreater(len(self.parser.anchor_targets), 0, "No internal anchor links found")
        for target in self.parser.anchor_targets:
            with self.subTest(anchor_target=target):
                self.assertIn(
                    target,
                    self.parser.ids,
                    f"Navigation link points to '#{target}', but no element with id='{target}' exists"
                )

    def test_critical_ui_elements_exist(self):
        """Modal lightbox and toast notification containers must exist."""
        required_ids = {"storyModal", "modalImg", "modalTitle", "modalStory", "modalTags", "toast"}
        for req_id in required_ids:
            with self.subTest(required_id=req_id):
                self.assertIn(req_id, self.parser.ids, f"Required UI element with id='{req_id}' is missing")

    def test_javascript_story_data_integrity(self):
        """All 5 Lego stories in JavaScript must have required fields and existing images."""
        expected_stories = ["piano", "coffee", "hardware", "cycling", "family"]
        for story_key in expected_stories:
            with self.subTest(story_key=story_key):
                self.assertIn(f"{story_key}:", self.html_content, f"Story key '{story_key}' not defined in JS")

        # Extract image paths referenced inside stories object
        story_img_matches = re.findall(r'img:\s*["\']([^"\']+)["\']', self.html_content)
        self.assertEqual(len(story_img_matches), 5, f"Expected 5 story images, found {len(story_img_matches)}")
        for img_rel in story_img_matches:
            full_path = os.path.join(BASE_DIR, img_rel)
            self.assertTrue(os.path.isfile(full_path), f"Image referenced in JS does not exist: {full_path}")


if __name__ == "__main__":
    unittest.main()
