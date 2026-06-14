"""今日播报 · 主编排。

两种跑法，用来把 slides 第 3 幕的 context 工程**量**出来：

  python run_broadcast.py --naive   # 反面教材：所有源的内容塞进一个主上下文，看 input_tokens 爆炸
  python run_broadcast.py           # 正确版：每个源派子 agent 只回传摘要（隔离）；主流程只攥轻量条目（按需检索）

跑完对比两次打印的 input_tokens —— 那个差距就是「隔离 + 按需检索」省下来的钱和注意力。
"""
import os
import re
import sys
import httpx
import yaml
from dotenv import load_dotenv

from broadcast.sources import arxiv, hackernews, github_trending
from broadcast.summarize import summarize_source
from broadcast import digest, deliver
from broadcast.agent_llm import complete, text_of

load_dotenv()
CFG = yaml.safe_load(open(os.path.join(os.path.dirname(__file__), "config.yaml"), encoding="utf-8"))
SOURCES = {"arxiv": arxiv, "hackernews": hackernews, "github_trending": github_trending}

# 反面教材（--naive）专用：去抓每条链接的【整页正文】。
# 这正是 slides 第 1 幕说的「全文 PDF、整页 HTML 全塞进上下文」——又贵又慢，正是反面教材该有的样子。
_full_client = httpx.Client(timeout=8, follow_redirects=True, headers={"User-Agent": "ParallightLab/2"})


def _full_page_text(url: str, limit: int = 4000) -> str:
    try:
        r = _full_client.get(url)
        txt = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", r.text, flags=re.S | re.I)  # 去脚本/样式
        txt = re.sub(r"<[^>]+>", " ", txt)                                              # 粗暴去标签
        return " ".join(txt.split())[:limit]
    except Exception:
        return ""


def gather() -> dict:
    """按需检索（slides ④）：先只抓每个源的**轻量条目**（标题/链接/元数据），不抓正文。"""
    out = {}
    for name, mod in SOURCES.items():
        if not CFG["sources"][name]["enabled"]:
            continue
        try:
            out[name] = mod.fetch(CFG)
            print(f"  · {name}: 抓到 {len(out[name])} 条轻量条目")
        except Exception as e:
            # 别让一个源拖垮全局（arXiv 可能 429、GitHub 选择器可能失效）
            print(f"  ⚠️  {name} 抓取失败：{e}（跳过）")
    return out


def run_correct() -> str:
    print("📡 抓取（只取轻量条目）…")
    items_by_source = gather()
    kws = CFG["interests"]["keywords"]
    budget = CFG["limits"]["per_source_summary_tokens"]

    sub_tokens = 0
    summaries = []
    for name, items in items_by_source.items():
        # 隔离（slides ③）：每个源一个子 agent，干净窗口里读条目、只回传摘要
        res = summarize_source(name, items, kws, budget)
        sub_tokens += res["usage"].input_tokens
        summaries.append(f"### {res['source']}\n{res['summary']}")

    # 👉 指挥点 A：主流程只把『各源摘要』喂给最终编排 —— 原文从没进主窗口。
    #   试试：如果你在上面 gather() 里改成连每条的全文都带进来，再塞到这里，
    #   主上下文的 input_tokens 会怎样变？（这就是「无脑全塞」，见 --naive）
    joined = "\n\n".join(summaries)
    resp = complete(
        [{"role": "user", "content": f"把这些各源摘要合成一份精炼的今日播报（去重、按重要性排序、每条带链接）：\n\n{joined}"}],
        max_tokens=1500,
    )
    main_in = resp.usage.input_tokens
    body = text_of(resp)

    print(f"\n🔬 隔离 + 按需 —— 主上下文 input_tokens = {main_in}（只看摘要，没碰原文）")
    print(f"   子 agent 在各自窗口里另烧了 {sub_tokens} token 读条目，但那些 token **没进主窗口**。")

    # 卸载 + 压缩（slides ②①）：读回昨天播过的，去重
    seen = digest.load_seen()
    deduped = digest.dedup(body, seen)
    if deduped != body:
        print("   📎 去重：过滤掉了昨天已经播报过的条目（来自 digest.md）。")
    return deduped or body


def run_naive() -> str:
    """反面教材：把每个源的【整页正文】都塞进一个主上下文，再让主 agent 一起总结。
    刻意去抓每条链接的整页文本——这正是 slides 第 1 幕的「全文 PDF / 整页 HTML 全塞进上下文」。
    所以它又慢又贵（慢本身就是教学点：无脑全塞 = 又贵又慢又糊）。"""
    print("📡 抓取（无脑全塞：连每条链接的整页正文都抓回来，慢是正常的）…")
    items_by_source = gather()
    blob = []
    budget = 12  # 最多抓 12 条整页正文兜住演示时长；其余条目回退用摘要
    for name, items in items_by_source.items():
        for it in items:
            meta = it.get("meta", {})
            body = ""
            if budget > 0:
                body = _full_page_text(it["url"])
                if body:
                    budget -= 1
            body = body or meta.get("abstract") or meta.get("desc") or ""
            blob.append(f"[{it['source']}] {it['title']}\n{body}\n{it['url']}")
    big = "\n\n".join(blob)
    resp = complete(
        [{"role": "user", "content": f"把下面所有内容总结成今日播报：\n\n{big}"}],
        max_tokens=2000,
    )
    print(f"\n🔬 无脑全塞 —— 主上下文 input_tokens = {resp.usage.input_tokens}（连整页正文都进了主窗口；又慢又贵）")
    return text_of(resp)


def main() -> None:
    naive = "--naive" in sys.argv
    title = CFG["delivery"]["title"]

    if naive:
        run_naive()
        print("\n（这是对照实验，不投递。对比它和正常跑的 input_tokens —— 这就是 slides 第 3 幕③④省下的东西。）")
        return

    body = run_correct()

    # 投递（slides 第 7 幕）——渠道由 config.yaml 决定：gmail（演示默认）/ feishu / local
    channel = CFG["delivery"]["channel"]
    r = deliver.deliver(channel, title, body)
    print(f"\n📤 投递（channel={channel}）：{r}")
    if not r.get("ok"):
        print("   （没发成功也没关系——本地 digest.md 仍会写。看 reason 定位『没发出去(transport)』还是『发了没收到』。）")

    # 卸载：写回窗口外，明天读回来续上 + 去重
    digest.append(title, body)
    print("📝 已写入 digest.md（明天/下次重跑会据此去重——这就是『记忆在文件不在模型』）")


if __name__ == "__main__":
    main()
