#!/usr/bin/env python3
"""钥匙级学习单测：纯 learning.py + 接 prefs.db。"""
import json, os, sys, tempfile, unittest, datetime
from pathlib import Path

BIN = Path(__file__).resolve().parents[1] / "bin"
sys.path.insert(0, str(BIN))
import learning
import prefs

NOW = 1_800_000_000_000  # ms


def fb(**kw):
    return learning.Feedback(kw, NOW)


class LearningPure(unittest.TestCase):
    def test_constants(self):
        self.assertEqual((learning.BOOST_PER, learning.BOOST_CAP, learning.PENALTY_FLOOR), (0.08, 0.30, 0.4))
        self.assertEqual(learning.DISLIKE_WEIGHT, 0.5)

    def test_dislike_specific_repo(self):
        one = fb(disliked=[{"id": "a", "at": NOW, "keys": ["repo:a/b"], "weight": 0.5}])
        self.assertEqual(one.factor(["repo:a/b"]), 0.875)  # 1 - 0.25*0.5
        self.assertEqual(one.factor(["repo:other/x"]), 1.0)

    def test_kw_gated_and_brand_exempt(self):
        d = fb(disliked=[{"id": "a", "at": NOW, "keys": ["kw:scion", "kw:claude", "feed:openai-news", "x:@q"], "weight": 0.5}])
        self.assertEqual(d.factor(["kw:scion"]), 1.0)
        self.assertEqual(d.factor(["feed:openai-news"]), 1.0)
        self.assertEqual(d.factor(["kw:claude"]), 1.0)
        self.assertLess(d.factor(["x:@q"]), 1.0)
        d2 = fb(disliked=[{"id": i, "at": NOW, "keys": ["kw:scion", "kw:claude"], "weight": 0.5} for i in "ab"])
        self.assertLess(d2.factor(["kw:scion"]), 1.0)
        self.assertEqual(d2.factor(["kw:claude"]), 1.0)

    def test_dismiss_never_in_action_side(self):
        self.assertIsNone(learning.ACTION_SIDE["dismiss"])
        self.assertIsNone(learning.ACTION_SIDE["skip"])
        self.assertIsNone(learning.ACTION_SIDE["read"])

    def test_boost_cap(self):
        b = fb(liked=[{"id": f"l{i}", "at": NOW, "keys": ["x:@good", "repo:g/h"], "weight": 1.5} for i in range(4)])
        self.assertEqual(b.factor(["x:@good", "repo:g/h"]), 1.3)
        self.assertEqual(fb(liked=[{"id": "l", "at": NOW, "keys": ["x:@good"]}]).factor(["x:@good"]), 1.08)

    def test_item_keys_x_and_repo_and_broad(self):
        keys = learning.item_keys({
            "url": "https://x.com/ufotable/status/1",
            "author": "ufotable",
            "source_type": "news",
            "source": "news",
            "topic": "二次元/ACG",
            "tags": ["topic:二次元/ACG", "src:x"],
            "item_id": "x:1",
        })
        self.assertIn("x:@ufotable", keys)
        # 大话题不进 kw
        self.assertFalse(any(k.startswith("kw:") and "二次元" in k for k in keys))
        self.assertFalse(any(k == "kw:ai" for k in keys))

        keys2 = learning.item_keys({
            "url": "https://github.com/deepseek-ai/dsh-superagent-prototype",
            "source": "github",
            "source_type": "github",
            "author": "deepseek-ai",
            "topic": "TypeScript",
            "tags": ["topic:TypeScript"],
        })
        self.assertIn("repo:deepseek-ai/dsh-superagent-prototype", keys2)
        # TypeScript 在 BROAD 里
        self.assertNotIn("kw:typescript", keys2)

    def test_floor_many_penalties(self):
        many = fb(trashed=[{"id": f"t{i}", "at": NOW, "keys": ["x:@q", "sub:y", "repo:a/b"]} for i in range(5)],
                  disliked=[{"id": "d", "at": NOW, "keys": ["x:@q"], "weight": 0.5}])
        self.assertEqual(many.factor(["x:@q", "sub:y", "repo:a/b"]), 0.4)


class PrefsIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        self.db = self.tmp.name
        self.c = prefs.connect(self.db)

    def tearDown(self):
        self.c.close()
        os.unlink(self.db)

    def _sig(self, **kw):
        d = {"source_type": "news", "action": "dislike", "user": "jidadiao", **kw}
        return prefs.add_signal(self.c, d)

    def test_dismiss_accepted_zero_weight(self):
        r = self._sig(action="dismiss", item_id="x:111", item_url="https://x.com/a/status/111",
                      title="收起测试", author="a", topic="AI", tags=["topic:AI"])
        self.assertIn("id", r)
        fb = prefs.feedback_from_db(self.c)
        self.assertEqual(fb.factor(["x:@a"]), 1.0)

    def test_dislike_anime_author_penalises(self):
        for i, author in enumerate(["ufotable", "Anime_ABEMA", "FateGrandOrder"]):
            self._sig(action="dislike", item_id=f"x:{100+i}", item_url=f"https://x.com/{author}/status/{100+i}",
                      title=f"动画{i}", author=author, topic="二次元/ACG", tags=["topic:二次元/ACG", "src:x"])
        fb = prefs.feedback_from_db(self.c)
        self.assertLess(fb.factor(["x:@ufotable"]), 1.0)
        # 大话题 AI 不被这些踩带偏
        self.assertEqual(fb.factor(["kw:ai"]), 1.0)

        card = {"url": "https://x.com/ufotable/status/999", "author": "ufotable", "source_type": "news",
                "topic": "二次元/ACG", "tags": ["topic:二次元/ACG"], "item_id": "x:999"}
        info = prefs.item_factor(self.c, card, fb=fb)
        self.assertLess(info["factor"], 1.0)
        self.assertIn("x:@ufotable", info["keys"])

    def test_manual_anime_hard_floors(self):
        prefs.remember(self.c, "不要再推动画", polarity="avoid", scope="topic", key="anime-hard")
        # 没有 dislike 信号，仅 manual
        card = {"url": "https://x.com/someone/status/1", "author": "someone", "source_type": "news",
                "topic": "二次元/ACG", "tags": ["topic:二次元/ACG"], "title": "新作动画 PV", "item_id": "x:1"}
        info = prefs.item_factor(self.c, card)
        self.assertEqual(info["factor"], learning.PENALTY_FLOOR)
        self.assertTrue(any("anime" in n for n in info["manual"]))

    def test_clear_key_revokes_penalty(self):
        self._sig(action="dislike", item_id="x:55", item_url="https://x.com/badacct/status/55",
                  title="踩", author="badacct", topic="AI", tags=["src:x"])
        fb = prefs.feedback_from_db(self.c)
        self.assertLess(fb.factor(["x:@badacct"]), 1.0)
        prefs.clear_learned_key(self.c, "x:@badacct", kind="penalty")
        fb2 = prefs.feedback_from_db(self.c)
        self.assertEqual(fb2.factor(["x:@badacct"]), 1.0)

    def test_like_boosts(self):
        self._sig(action="like", item_id="x:77", item_url="https://x.com/goodone/status/77",
                  title="赞", author="goodone", topic="中转站/VPS/自建", tags=["src:x"])
        info = prefs.item_factor(self.c, {"url": "https://x.com/goodone/status/88", "author": "goodone",
                                          "source_type": "news", "item_id": "x:88"})
        self.assertGreater(info["factor"], 1.0)

    def test_learned_cli_shape(self):
        self._sig(action="dislike", item_id="repo:x/y", item_url="https://github.com/aa/bb",
                  title="gh", author="aa", topic="Python", source_type="github", tags=["topic:Python"])
        # fix: source_type in add_signal - need pass correctly
        out = prefs.learned_keys(self.c, limit=20)
        self.assertIn("keys", out)
        self.assertEqual(out["half_life_days"], 30)


class VpsDbSmoke(unittest.TestCase):
    """对 VPS 副本只读冒烟（有则跑）。"""
    DB = "/tmp/prefs-vps.db"

    @classmethod
    def setUpClass(cls):
        if not os.path.isfile(cls.DB):
            raise unittest.SkipTest("no vps db copy")

    def test_export_learned_and_anime_penalty(self):
        c = prefs.connect(self.DB)
        try:
            out = prefs.learned_keys(c, limit=100)
            keys = {x["key"] for x in out["keys"]}
            # 多次踩过的动画作者应出现在 penalty
            anime_authors = [k for k in keys if k.startswith("x:@") and k in {
                "x:@ufotable", "x:@anime_abema", "x:@fategrandorder", "x:@syaoran996", "x:@hacken2006"
            }]
            self.assertTrue(anime_authors, f"expected anime author penalties, got sample={list(keys)[:20]}")
            # 大话题不该作为 kw 被惩罚到离谱
            self.assertNotIn("kw:ai", keys)
            card = {"url": "https://x.com/ufotable/status/1", "author": "ufotable", "source_type": "news",
                    "topic": "二次元/ACG", "tags": ["topic:二次元/ACG"], "title": "动画", "item_id": "x:1"}
            info = prefs.item_factor(c, card)
            self.assertLess(info["factor"], 0.95)
            # profile 带 keys
            p = prefs.profile(c, top=8)
            self.assertIn("keys", p)
            self.assertIn("top", p["keys"])
        finally:
            c.close()


if __name__ == "__main__":
    unittest.main()
