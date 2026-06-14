// dashboard-data.js — 常驻 dashboard 的数据源（模板占位版）。
// Parallight 不变要求：课程每一步都可视化。学习者每跑完一个实验，
// Mentor 就往 window.DASHBOARD 末尾 append 一条 {key,label,file,hint,code,steps}。
// HTML(tool-mechanism.html) 会自动按这个数组生成 tab —— append 时不用碰 HTML。
//
// entry schema:
//   { key:'唯一英文短名', label:'① 一句话标题', file:'对应的源文件',
//     hint:'这个实验一句话看到了什么',
//     code:[[行号, '<该行高亮 HTML>'], …],
//     steps:[{ n:'STEP 1', t:'这一步在干嘛', who:'model|you|spec', whoTxt:'谁在动手',
//              lines:[行号…], io:'<这一步真实的请求/返回/输出 HTML>' }, …] }

window.DASHBOARD = [
  { key:'mcp-config', label:'① 一段 config → 一排工具凭空出现', file:'.mcp.json',
    hint:'用别人的 MCP = 加一段 command/args，client 自动 tools/list 发现工具；你没写一行实现。',
    code:[
      [3, '  <span class="str">"github"</span>: {'],
      [4, '    <span class="kw">"command"</span>: <span class="str">"npx"</span>,'],
      [5, '    <span class="kw">"args"</span>: [<span class="str">"-y"</span>, <span class="str">"@modelcontextprotocol/server-github"</span>],'],
      [7, '    <span class="kw">"GITHUB_PERSONAL_ACCESS_TOKEN"</span>: <span class="str">"${GITHUB_PERSONAL_ACCESS_TOKEN}"</span>']
    ],
    steps:[
      { n:'STEP 1', t:'MCP Inspector tools/list dump', who:'you', whoTxt:'你当 client',
        lines:[5],
        io:'<div class="card"><div class="box">{ "tools": [ { "name": "create_or_update_file", ... }, { "name": "search_repositories", ... }, { "name": "create_repository", ... }, ... ] }<br><br>→ 工具凭空出现，没有本地实现代码</div></div>' },
      { n:'STEP 2', t:'GitHub API 真实返回（等价 MCP tools/call）', who:'model', whoTxt:'agent 调用',
        lines:[6,7],
        io:'<div class="card"><div class="box">#1677 fix: resolve x-stainless-timeout ...<br>#1676 x-stainless-timeout header is NOT_GIVEN ...<br>#1675 Fix: add missing .stream() method ...<br>→ anthropics/anthropic-sdk-python 最新 issues</div></div>' }
    ]
  },
  { key:'isolation-jit', label:'② 隔离 + 按需检索：input_tokens 对照', file:'run_broadcast.py',
    hint:'子 agent 在干净窗口读原文只回传摘要；主流程只攥指针按需抓取。主窗口缩小 11 倍。',
    code:[
      [1, '<span class="cmt"># --naive：全文塞进主上下文</span>'],
      [2, '<span class="cmt"># 正常版：每源派子 agent，只回传摘要</span>']
    ],
    steps:[
      { n:'STEP 1', t:'naive 跑法（全塞）', who:'you', whoTxt:'对照实验',
        lines:[1],
        io:'<div class="card"><div class="box">主上下文 input_tokens = <strong>12,373</strong><br>三个源原文全进主窗口 → 又慢又贵</div></div>' },
      { n:'STEP 2', t:'隔离 + 按需（正确版）', who:'you', whoTxt:'真实跑法',
        lines:[2],
        io:'<div class="card"><div class="box">主上下文 input_tokens = <strong>1,081</strong><br>子 agent 另烧 2,173（留在子窗口）<br>→ 主窗口缩小 <strong>11 倍</strong></div></div>' }
    ]
  },
];
