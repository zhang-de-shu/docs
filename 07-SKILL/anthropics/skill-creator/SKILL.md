---
name: skill-creator
description: 创建新技能、修改和改进现有技能，以及衡量技能性能。当用户想从零创建技能、编辑或优化现有技能、运行 eval 测试技能、通过方差分析对技能性能进行基准测试，或优化技能的 description 以提升触发准确率时使用。
---

# Skill Creator

一个用于创建新技能并对其进行迭代改进的技能。

从宏观上看，创建一个技能的流程大致如下：

- 确定你希望这个技能做什么，以及它大致应该如何做
- 撰写技能的初稿
- 创建几个测试 prompt，并在"可访问该技能的 Claude"上运行它们
- 协助用户从定性和定量两方面评估结果
  - 在这些运行于后台进行的同时，如果还没有定量评估就起草一些（如果已经有了，你可以照原样使用，或者在觉得需要改动时进行修改）。然后向用户解释它们（或者如果它们本就存在，就解释已有的那些）
  - 使用 `eval-viewer/generate_review.py` 脚本把结果展示给用户查看，同时也让他们查看定量指标
- 根据用户对结果的评估反馈（以及若定量基准中暴露出任何明显缺陷）重写该技能
- 重复直到你满意为止
- 扩充测试集，并在更大规模上再试一次

使用该技能时，你的工作是弄清用户目前处于这一流程的哪个阶段，然后介入并帮助他们推进这些阶段。举例来说，也许他们会说"我想做一个针对 X 的技能"。你可以帮忙厘清他们的意思、写一份初稿、写测试用例、弄清他们想如何评估、运行所有的 prompt，然后重复。

另一方面，也许他们已经有了技能的初稿。在这种情况下，你可以直接进入循环中的评估/迭代部分。

当然，你应始终保持灵活，如果用户说"我不需要运行一堆评估，跟着感觉走就行"，那你也可以照做。

然后在技能完成之后（不过再次强调，顺序是灵活的），你还可以运行技能描述改进器——我们为此专门准备了一个单独的脚本——来优化技能的触发。

明白了吗？很好。

## 与用户沟通

技能创建器很可能被熟悉编程术语程度参差不齐的各类人群使用。如果你还没听说过（你又怎么会听说过呢，毕竟这才是最近才开始的），如今出现了一种趋势：Claude 的能力正激励着水管工去打开他们的终端，让父母和祖父母去谷歌搜索"how to install npm"。另一方面，绝大多数用户大概相当具备计算机素养。

所以请留意上下文线索，以理解该如何措辞进行沟通！在默认情况下，仅给你一点概念：

- "evaluation" 和 "benchmark" 处于模棱两可的边界，但尚可接受
- 对于 "JSON" 和 "assertion"，你要先从用户那里看到确凿的线索、表明他们知道这些是什么东西，然后才能不加解释地使用它们

如果拿不准，简要解释一下术语是可以的；如果不确定用户能否理解，也尽管用简短的定义把术语说清楚。

---

## 创建技能

### 捕捉意图

先从理解用户的意图开始。当前对话中可能已经包含了用户想要捕捉的某个工作流（例如他们说 "turn this into a skill"）。如果是这样，先从对话历史中提取答案——所用的工具、步骤的顺序、用户做出的纠正、观察到的输入/输出格式。用户可能需要补上空缺，并应在进入下一步之前予以确认。

1. 这个技能应该让 Claude 能够做什么？
2. 这个技能应该在什么时候触发？（哪些用户措辞/情境）
3. 期望的输出格式是什么？
4. 我们是否应该建立测试用例来验证该技能能正常工作？输出可客观验证的技能（文件转换、数据提取、代码生成、固定的工作流步骤）能从测试用例中受益。输出较为主观的技能（写作风格、艺术创作）通常不需要。根据技能类型给出合适的默认建议，但把决定权留给用户。

### 访谈与调研

主动就边界情况、输入/输出格式、示例文件、成功标准和依赖项提出问题。在把这部分敲定之前，先不要着急写测试 prompt。

检查可用的 MCP——如果对调研有用（搜索文档、查找相似技能、查阅最佳实践），在可用时通过子代理并行调研，否则就内联进行。带着充分的上下文前来，以减轻用户的负担。

### 编写 SKILL.md

基于对用户的访谈，填充以下各个组成部分：

- **name**：技能标识符
- **description**：何时触发、它做什么。这是主要的触发机制——既要包含技能做什么，也要包含具体的使用情境。所有"何时使用"的信息都放在这里，而不是放在正文中。注意：目前 Claude 有一种"触发不足"的倾向——在本该有用时却不去使用技能。为了对抗这一点，请把技能描述写得稍微"主动积极"一些。例如，与其写 "How to build a simple fast dashboard to display internal Anthropic data."，你可以写 "How to build a simple fast dashboard to display internal Anthropic data. Make sure to use this skill whenever the user mentions dashboards, data visualization, internal metrics, or wants to display any kind of company data, even if they don't explicitly ask for a 'dashboard.'"
- **compatibility**：所需工具、依赖项（可选，很少需要）
- **技能的其余部分 :)**

### 技能编写指南

#### 技能的结构剖析

```
skill-name/
├── SKILL.md (required)
│   ├── YAML frontmatter (name, description required)
│   └── Markdown instructions
└── Bundled Resources (optional)
    ├── scripts/    - Executable code for deterministic/repetitive tasks
    ├── references/ - Docs loaded into context as needed
    └── assets/     - Files used in output (templates, icons, fonts)
```

#### 渐进式披露（Progressive Disclosure）

技能使用一套三层加载系统：
1. **元数据（Metadata）**（name + description）——始终在上下文中（约 100 词）
2. **SKILL.md 正文**——技能触发时即在上下文中（理想情况 <500 行）
3. **捆绑资源（Bundled resources）**——按需加载（无限制，脚本无需加载即可执行）

这些词数是近似值，如有需要，尽可以写得更长。

**关键模式：**
- 让 SKILL.md 保持在 500 行以内；如果快要接近这个上限，就再增加一层层级结构，并附上清晰的指引，说明使用该技能的模型接下来应去哪里跟进查阅。
- 在 SKILL.md 中清晰地引用各文件，并给出何时该阅读它们的指引
- 对于较大的引用文件（>300 行），加上一个目录

**领域组织**：当一个技能支持多个领域/框架时，按变体来组织：
```
cloud-deploy/
├── SKILL.md (workflow + selection)
└── references/
    ├── aws.md
    ├── gcp.md
    └── azure.md
```
Claude 只阅读相关的那个引用文件。

#### 不出意外原则（Principle of Lack of Surprise）

这本不必多说，但技能绝不能包含恶意软件、漏洞利用代码，或任何可能危及系统安全的内容。一个技能的内容，若加以描述，其意图不应让用户感到意外。不要配合创建具有误导性的技能，或旨在助长未经授权的访问、数据外泄或其他恶意活动的技能。不过，诸如"扮演某个 XYZ 角色"之类的东西是可以的。

#### 编写模式

在指令中优先使用祈使句形式。

**定义输出格式**——你可以这样做：
```markdown
## Report structure
ALWAYS use this exact template:
# [Title]
## Executive summary
## Key findings
## Recommendations
```

**示例模式**——加入示例很有用。你可以这样格式化它们（但如果示例中出现了 "Input" 和 "Output"，你或许想稍作变通）：
```markdown
## Commit message format
**Example 1:**
Input: Added user authentication with JWT tokens
Output: feat(auth): implement JWT-based authentication
```

### 写作风格

尽量向模型解释为什么某些事情很重要，而不要用生硬陈腐的 MUST。运用心智理论（theory of mind），努力让技能具有普适性，而不要过于狭隘地针对特定示例。先写一份初稿，然后以全新的眼光审视它并加以改进。

### 测试用例

写完技能初稿后，想出 2-3 个真实的测试 prompt——那种真实用户实际会说出来的话。把它们分享给用户：[你不必用这一模一样的措辞] "Here are a few test cases I'd like to try. Do these look right, or do you want to add more?" 然后运行它们。

把测试用例保存到 `evals/evals.json`。先不要写断言（assertions）——只写 prompt。你将在下一步、也就是运行进行中的同时起草断言。

```json
{
  "skill_name": "example-skill",
  "evals": [
    {
      "id": 1,
      "prompt": "User's task prompt",
      "expected_output": "Description of expected result",
      "files": []
    }
  ]
}
```

完整的 schema（包括你稍后将添加的 `assertions` 字段）见 `references/schemas.md`。

## 运行并评估测试用例

本节是一个连续的序列——不要中途停下。请勿使用 `/skill-test` 或任何其他测试技能。

把结果放在与技能目录同级的 `<skill-name>-workspace/` 中。在该工作区内，按迭代（`iteration-1/`、`iteration-2/` 等）组织结果，并在其内为每个测试用例分配一个目录（`eval-0/`、`eval-1/` 等）。不要一开始就把这些全部建好——边做边创建目录即可。

### 步骤 1：在同一回合内启动所有运行（with-skill 和 baseline）

对每个测试用例，在同一回合内启动两个子代理——一个带技能，一个不带。这一点很重要：不要先启动 with-skill 的运行、之后再回头补做 baseline。一次性把所有的都启动起来，好让它们都在差不多同一时间完成。

**With-skill 运行：**

```
Execute this task:
- Skill path: <path-to-skill>
- Task: <eval prompt>
- Input files: <eval files if any, or "none">
- Save outputs to: <workspace>/iteration-<N>/eval-<ID>/with_skill/outputs/
- Outputs to save: <what the user cares about — e.g., "the .docx file", "the final CSV">
```

**Baseline 运行**（相同的 prompt，但 baseline 取决于场景）：
- **创建一个新技能**：完全不带技能。相同的 prompt，不带技能路径，保存到 `without_skill/outputs/`。
- **改进一个现有技能**：使用旧版本。在编辑之前，先给技能拍个快照（`cp -r <skill-path> <workspace>/skill-snapshot/`），然后让 baseline 子代理指向该快照。保存到 `old_skill/outputs/`。

为每个测试用例写一个 `eval_metadata.json`（断言暂时可以为空）。根据每个 eval 所测试的内容为其取一个描述性的名字——而不只是 "eval-0"。目录也使用这个名字。如果本次迭代使用了新的或修改过的 eval prompt，就为每个新的 eval 目录创建这些文件——不要以为它们会从之前的迭代沿用过来。

```json
{
  "eval_id": 0,
  "eval_name": "descriptive-name-here",
  "prompt": "The user's task prompt",
  "assertions": []
}
```

### 步骤 2：在运行进行中的同时，起草断言

不要只是干等运行结束——你可以把这段时间用得富有成效。为每个测试用例起草定量断言，并向用户解释它们。如果 `evals/evals.json` 中已存在断言，就审阅它们并解释它们检查的是什么。

好的断言是可客观验证的，并且带有描述性的名字——它们在基准查看器中应清晰易读，好让扫一眼结果的人立刻明白每一条检查的是什么。主观性技能（写作风格、设计质量）更适合定性评估——不要把断言强加到那些需要人类判断的东西上。

断言起草完毕后，用它们更新 `eval_metadata.json` 各文件以及 `evals/evals.json`。同时也向用户解释他们将在查看器中看到什么——既有定性的输出，也有定量的基准。

### 步骤 3：随着运行完成，捕获计时数据

当每个子代理任务完成时，你会收到一条包含 `total_tokens` 和 `duration_ms` 的通知。立即把这份数据保存到运行目录下的 `timing.json`：

```json
{
  "total_tokens": 84852,
  "duration_ms": 23332,
  "total_duration_seconds": 23.3
}
```

这是捕获这份数据的唯一机会——它通过任务通知传来，别处不会持久化保存。每条通知一到就处理，而不要试图把它们攒到一起批处理。

### 步骤 4：评分、汇总并启动查看器

一旦所有运行完成：

1. **给每次运行评分**——启动一个评分员子代理（或内联评分），让它读取 `agents/grader.md` 并针对输出评估每一条断言。把结果保存到每个运行目录下的 `grading.json`。grading.json 的 expectations 数组必须使用字段 `text`、`passed` 和 `evidence`（而不是 `name`/`met`/`details` 或其他变体）——查看器依赖于这些确切的字段名。对于可以通过程序检查的断言，写一个脚本来运行，而不要靠肉眼查看——脚本更快、更可靠，而且可以跨迭代复用。

2. **汇总为基准**——从 skill-creator 目录运行汇总脚本：
   ```bash
   python -m scripts.aggregate_benchmark <workspace>/iteration-N --skill-name <name>
   ```
   这会生成 `benchmark.json` 和 `benchmark.md`，其中包含每种配置的 pass_rate、时间和 token，附有均值 ± 标准差以及差值（delta）。如果手动生成 benchmark.json，查看器所期望的确切 schema 见 `references/schemas.md`。
把每个 with_skill 版本放在其对应的 baseline 之前。

3. **做一遍分析师复查**——阅读基准数据，揭示出汇总统计数据可能掩盖的模式。要留意什么，见 `agents/analyzer.md`（"Analyzing Benchmark Results" 一节）——诸如无论有无技能都总是通过的断言（不具区分度）、高方差的 eval（可能不稳定/flaky），以及时间/token 之间的权衡。

4. **启动查看器**，同时提供定性输出和定量数据：
   ```bash
   nohup python <skill-creator-path>/eval-viewer/generate_review.py \
     <workspace>/iteration-N \
     --skill-name "my-skill" \
     --benchmark <workspace>/iteration-N/benchmark.json \
     > /dev/null 2>&1 &
   VIEWER_PID=$!
   ```
   对于第 2 次及以后的迭代，还要传入 `--previous-workspace <workspace>/iteration-<N-1>`。

   **Cowork / 无头（headless）环境：** 如果 `webbrowser.open()` 不可用，或环境没有显示器，就使用 `--static <output_path>` 来写出一个独立的 HTML 文件，而不是启动一个服务器。当用户点击 "Submit All Reviews" 时，反馈会作为一个 `feedback.json` 文件被下载下来。下载后，把 `feedback.json` 复制到工作区目录，以便下一次迭代读取。

注意：请使用 generate_review.py 来创建查看器；无需自己写自定义 HTML。

5. **告诉用户**类似这样的话："I've opened the results in your browser. There are two tabs — 'Outputs' lets you click through each test case and leave feedback, 'Benchmark' shows the quantitative comparison. When you're done, come back here and let me know."

### 用户在查看器中看到什么

"Outputs" 标签页一次显示一个测试用例：
- **Prompt**：所给出的任务
- **Output**：技能所产出的文件，尽可能内联渲染
- **Previous Output**（第 2 次及以后的迭代）：折叠的部分，显示上一次迭代的输出
- **Formal Grades**（如果运行了评分）：折叠的部分，显示断言的通过/失败
- **Feedback**：一个随着输入自动保存的文本框
- **Previous Feedback**（第 2 次及以后的迭代）：他们上次的评论，显示在文本框下方

"Benchmark" 标签页显示统计摘要：每种配置的通过率、计时和 token 使用量，附有逐个 eval 的细分以及分析师的观察。

导航通过 prev/next 按钮或方向键完成。完成后，他们点击 "Submit All Reviews"，这会把所有反馈保存到 `feedback.json`。

### 步骤 5：阅读反馈

当用户告诉你他们完成了，读取 `feedback.json`：

```json
{
  "reviews": [
    {"run_id": "eval-0-with_skill", "feedback": "the chart is missing axis labels", "timestamp": "..."},
    {"run_id": "eval-1-with_skill", "feedback": "", "timestamp": "..."},
    {"run_id": "eval-2-with_skill", "feedback": "perfect, love this", "timestamp": "..."}
  ],
  "status": "complete"
}
```

空的反馈意味着用户认为它没问题。把你的改进精力集中在用户有具体抱怨的那些测试用例上。

用完查看器后，把它的服务器关掉：

```bash
kill $VIEWER_PID 2>/dev/null
```

---

## 改进技能

这是整个循环的核心。你已经运行了测试用例，用户也审阅了结果，现在你需要根据他们的反馈把技能做得更好。

### 如何思考改进

1. **从反馈中提炼出普遍规律。** 这里正在发生的宏观图景是：我们试图创建能被使用上百万次（也许真的是字面意义上的，甚至更多，谁知道呢）、横跨许多不同 prompt 的技能。在此，你和用户只是反复在少数几个示例上迭代，因为这有助于更快地推进。用户对这些示例了如指掌，评估新输出对他们来说很快。但如果你和用户共同开发出的技能只对那些示例有效，它就毫无用处。与其塞入琐碎、过拟合的改动，或压迫性、过度约束的 MUST，不如在遇到某个顽固问题时，尝试拓展开去、使用不同的比喻，或推荐不同的工作模式。尝试的成本相对较低，说不定你就撞上了某个绝妙的方案。

2. **保持 prompt 精简。** 去掉那些没有发挥作用的东西。务必阅读运行记录（transcript），而不只是看最终输出——如果看起来技能让模型浪费了大把时间去做一些无成效的事情，你可以试着去掉技能中导致这种情况的部分，看看会发生什么。

3. **解释缘由。** 努力去解释你要求模型做的每一件事背后的**缘由**。今天的 LLM 很*聪明*。它们有良好的心智理论，在给予好的支架（harness）时，能够超越死板的指令，真正把事情办成。即便用户的反馈简短或带着挫败情绪，也要努力真正理解任务、理解用户为什么写下他们所写的内容、他们究竟写了什么，然后把这份理解注入到指令之中。如果你发现自己在全大写地写 ALWAYS 或 NEVER，或者在用极其僵硬的结构，那是一个黄色警示——如果可能，重新组织表述并解释其中的道理，好让模型理解你所要求的东西为什么重要。那是一种更人性化、更有力、更有效的做法。

4. **留意跨测试用例的重复工作。** 阅读各次测试运行的记录，注意子代理是否都各自独立地写了相似的辅助脚本，或对某件事采取了同样的多步做法。如果 3 个测试用例都导致子代理写了一个 `create_docx.py` 或 `build_chart.py`，那是一个强烈的信号，说明技能应当把那个脚本捆绑进来。写一次，放进 `scripts/`，然后告诉技能去使用它。这能让未来每一次调用都免于重新造轮子。

这项任务相当重要（我们可是在试图每年创造数十亿的经济价值！），而你的思考时间并不是瓶颈；从容一些，认真地把事情想透。我建议先写一份修订初稿，然后重新审视它并做出改进。真正尽你所能去设身处地地体会用户，理解他们想要什么、需要什么。

### 迭代循环

改进技能之后：

1. 把你的改进应用到技能上
2. 把所有测试用例重新运行到一个新的 `iteration-<N+1>/` 目录里，包括 baseline 运行。如果你是在创建一个新技能，baseline 始终是 `without_skill`（不带技能）——它在各次迭代中保持不变。如果你是在改进一个现有技能，就凭你的判断来决定什么作为 baseline 更合理：用户最初带来的原始版本，还是上一次迭代。
3. 启动查看器，并把 `--previous-workspace` 指向上一次迭代
4. 等待用户审阅并告诉你他们完成了
5. 阅读新的反馈，再次改进，重复

一直进行下去，直到：
- 用户说他们满意了
- 反馈全都是空的（一切看起来都不错）
- 你已经没有在取得有意义的进展

---

## 进阶：盲对比（Blind comparison）

对于你想要在技能的两个版本之间做更严格对比的情形（例如用户问"新版本真的更好吗？"），有一套盲对比系统。细节见 `agents/comparator.md` 和 `agents/analyzer.md`。基本思路是：把两份输出交给一个独立的代理，不告诉它哪份是哪份，让它评判质量。然后分析胜出者为何胜出。

这是可选的，需要子代理，而且大多数用户不会用到。人工审阅循环通常已经足够。

---

## 描述优化

SKILL.md frontmatter 中的 description 字段是决定 Claude 是否调用某个技能的主要机制。在创建或改进技能之后，主动提出优化描述以获得更好的触发准确度。

### 步骤 1：生成触发评估查询

创建 20 个评估查询——混合 should-trigger 和 should-not-trigger。保存为 JSON：

```json
[
  {"query": "the user prompt", "should_trigger": true},
  {"query": "another prompt", "should_trigger": false}
]
```

这些查询必须真实，是 Claude Code 或 Claude.ai 用户实际会输入的东西。不是抽象的请求，而是具体、明确、带有相当细节量的请求。例如文件路径、关于用户工作或处境的个人背景、列名和取值、公司名、URL。带一点点来龙去脉。有些可以是小写，或包含缩写、拼写错误或随意的口语。使用不同长度的混合，并侧重边界情况，而不是把它们写得泾渭分明（用户会有机会对它们把关签字）。

不好的例子：`"Format this data"`、`"Extract text from PDF"`、`"Create a chart"`

好的例子：`"ok so my boss just sent me this xlsx file (its in my downloads, called something like 'Q4 sales final FINAL v2.xlsx') and she wants me to add a column that shows the profit margin as a percentage. The revenue is in column C and costs are in column D i think"`

对于 **should-trigger** 类查询（8-10 个），要考虑覆盖面。你需要同一意图的不同措辞——有些正式，有些随意。包括用户没有明确说出技能名或文件类型、但显然需要它的情形。加入一些不常见的用例，以及本技能与另一技能相互竞争但本技能应当胜出的情形。

对于 **should-not-trigger** 类查询（8-10 个），最有价值的是那些"擦肩而过"（near-miss）的——与技能共享关键词或概念、但实际需要别的东西的查询。想想相邻领域、含糊的措辞（天真的关键词匹配会触发但本不该触发），以及查询触及了技能所做之事、但所处情境下另一个工具更合适的情形。

要避免的关键点：不要把 should-not-trigger 类查询写得明显不相关。对一个 PDF 技能来说，用 "Write a fibonacci function" 作为负面测试太容易了——它什么也测不出来。负面用例应当是真正有迷惑性的。

### 步骤 2：与用户一起审阅

使用 HTML 模板把评估集呈现给用户审阅：

1. 从 `assets/eval_review.html` 读取模板
2. 替换其中的占位符：
   - `__EVAL_DATA_PLACEHOLDER__` → eval 项的 JSON 数组（外面不要加引号——它是一个 JS 变量赋值）
   - `__SKILL_NAME_PLACEHOLDER__` → 技能的名字
   - `__SKILL_DESCRIPTION_PLACEHOLDER__` → 技能当前的描述
3. 写入一个临时文件（例如 `/tmp/eval_review_<skill-name>.html`）并打开它：`open /tmp/eval_review_<skill-name>.html`
4. 用户可以编辑查询、切换 should-trigger、增删条目，然后点击 "Export Eval Set"
5. 文件会下载到 `~/Downloads/eval_set.json`——检查 Downloads 文件夹里最新的版本，以防出现多个（例如 `eval_set (1).json`）

这一步很重要——糟糕的评估查询会导致糟糕的描述。

### 步骤 3：运行优化循环

告诉用户："This will take some time — I'll run the optimization loop in the background and check on it periodically."

把评估集保存到工作区，然后在后台运行：

```bash
python -m scripts.run_loop \
  --eval-set <path-to-trigger-eval.json> \
  --skill-path <path-to-skill> \
  --model <model-id-powering-this-session> \
  --max-iterations 5 \
  --verbose
```

使用你系统提示中的模型 ID（即驱动当前会话的那个），这样触发测试才能与用户实际体验到的相符。

在它运行期间，定期 tail 输出，以便向用户更新它进行到第几次迭代、分数看起来如何。

这会自动处理完整的优化循环。它把评估集拆分为 60% 训练集和 40% 留出（held-out）测试集，评估当前的描述（每个查询运行 3 次以获得可靠的触发率），然后调用 Claude 基于失败之处提出改进建议。它会在训练集和测试集上重新评估每一个新描述，迭代至多 5 次。完成后，它会在浏览器中打开一个 HTML 报告，逐次迭代展示结果，并返回带有 `best_description` 的 JSON——按测试分数而非训练分数来选取，以避免过拟合。

### 技能触发的工作原理

理解触发机制有助于设计更好的评估查询。技能会以其 name + description 出现在 Claude 的 `available_skills` 列表中，Claude 基于该描述来决定是否查阅某个技能。要知道的重要一点是：Claude 只会为它自己无法轻松处理的任务去查阅技能——像 "read this PDF" 这样简单的一步查询，即便描述完全匹配也可能不会触发技能，因为 Claude 用基本工具就能直接处理它们。复杂的、多步的或专门的查询，在描述匹配时会可靠地触发技能。

这意味着你的评估查询应当足够有分量，让 Claude 确实能从查阅技能中受益。像 "read file X" 这样简单的查询是糟糕的测试用例——无论描述质量如何，它们都不会触发技能。

### 步骤 4：应用结果

从 JSON 输出中取出 `best_description`，并更新技能 SKILL.md 的 frontmatter。把前后对照展示给用户，并报告分数。

---

### 打包与呈现（仅当 `present_files` 工具可用时）

检查你是否有权访问 `present_files` 工具。如果没有，跳过此步骤。如果有，就打包技能并把 .skill 文件呈现给用户：

```bash
python -m scripts.package_skill <path/to/skill-folder>
```

打包之后，把用户引导到生成的 `.skill` 文件路径，以便他们安装。

---

## Claude.ai 专属说明

在 Claude.ai 中，核心工作流是相同的（起草 → 测试 → 审阅 → 改进 → 重复），但因为 Claude.ai 没有子代理，某些机制会有所变化。以下是需要适配的地方：

**运行测试用例**：没有子代理就意味着没有并行执行。对每个测试用例，读取技能的 SKILL.md，然后自己按照它的指令去完成该测试 prompt。一次做一个。这不如用独立的子代理那样严格（你既写了技能又在运行它，因此拥有全部上下文），但它是一个有用的合理性检查（sanity check）——而且人工审阅步骤可以起到弥补作用。跳过 baseline 运行——直接用技能按要求完成任务即可。

**审阅结果**：如果你无法打开浏览器（例如 Claude.ai 的 VM 没有显示器，或你在一台远程服务器上），就完全跳过浏览器审阅器。改为直接在对话中呈现结果。对每个测试用例，展示 prompt 和输出。如果输出是用户需要查看的文件（比如 .docx 或 .xlsx），就把它保存到文件系统，并告诉他们它在哪里，以便他们下载并检查。内联征求反馈："How does this look? Anything you'd change?"

**基准评测**：跳过定量基准评测——它依赖于 baseline 对比，而没有子代理这种对比就没有意义。把重点放在用户的定性反馈上。

**迭代循环**：与之前相同——改进技能、重跑测试用例、征求反馈——只是中间没有了浏览器审阅器。如果你有文件系统，仍然可以把结果组织到迭代目录中。

**描述优化**：本节需要 `claude` CLI 工具（具体是 `claude -p`），它仅在 Claude Code 中可用。如果你在 Claude.ai 上，就跳过它。

**盲对比**：需要子代理。跳过它。

**打包**：`package_skill.py` 脚本在任何具备 Python 和文件系统的地方都能工作。在 Claude.ai 上，你可以运行它，用户就能下载生成的 `.skill` 文件。

**更新一个现有技能**：用户可能是在要求你更新一个现有技能，而不是创建一个新的。在这种情况下：
- **保留原来的名字。** 记下技能的目录名和 `name` frontmatter 字段——原封不动地使用它们。例如，如果已安装的技能是 `research-helper`，就输出 `research-helper.skill`（而不是 `research-helper-v2`）。
- **在编辑前先复制到一个可写的位置。** 已安装技能的路径可能是只读的。复制到 `/tmp/skill-name/`，在那里编辑，并从副本打包。
- **如果手动打包，先在 `/tmp/` 中暂存**，然后再复制到输出目录——直接写入可能会因权限而失败。

---

## Cowork 专属说明

如果你在 Cowork 中，主要需要知道的是：

- 你有子代理，所以主工作流（并行启动测试用例、运行 baseline、评分等）全都可用。（不过，如果你遇到严重的超时问题，串行而非并行地运行测试 prompt 也是可以的。）
- 你没有浏览器或显示器，所以在生成评估查看器时，使用 `--static <output_path>` 写出一个独立的 HTML 文件，而不是启动一个服务器。然后提供一个链接，让用户可以点击它在浏览器中打开该 HTML。
- 不知何故，Cowork 的环境似乎让 Claude 在运行完测试后不太愿意去生成评估查看器，所以再重申一遍：无论你在 Cowork 还是在 Claude Code 中，运行完测试后，你都应当始终生成评估查看器供人类查看示例，之后你再自己修订技能并尝试做出纠正，使用 `generate_review.py`（不要写你自己的定制 html 代码）。先说声抱歉，我这里要全大写了：在你自己评估输入*之前* GENERATE THE EVAL VIEWER。你要尽快把它们摆到人类面前！
- 反馈的运作方式有所不同：由于没有正在运行的服务器，查看器的 "Submit All Reviews" 按钮会把 `feedback.json` 作为一个文件下载下来。你之后可以从那里读取它（你可能需要先请求访问权限）。
- 打包可用——`package_skill.py` 只需要 Python 和文件系统。
- 描述优化（`run_loop.py` / `run_eval.py`）在 Cowork 中应该也能正常工作，因为它通过 subprocess 使用 `claude -p`，而非浏览器，但请把它留到你完全做完技能、并且用户同意它已处于良好状态之后再进行。
- **更新一个现有技能**：用户可能是在要求你更新一个现有技能，而不是创建一个新的。遵循上文 claude.ai 一节中的更新指引。

---

## 参考文件

agents/ 目录包含面向专门子代理的指令。当你需要启动相应的子代理时再阅读它们。

- `agents/grader.md` — 如何针对输出评估断言
- `agents/comparator.md` — 如何在两份输出之间做盲 A/B 对比
- `agents/analyzer.md` — 如何分析为何一个版本胜过另一个

references/ 目录有额外的文档：
- `references/schemas.md` — evals.json、grading.json 等的 JSON 结构

---

为强调起见，在这里再重复一遍核心循环：

- 弄清技能是关于什么的
- 起草或编辑技能
- 在测试 prompt 上运行"可访问该技能的 Claude"
- 与用户一起评估输出：
  - 创建 benchmark.json 并运行 `eval-viewer/generate_review.py` 来帮助用户审阅它们
  - 运行定量评估
- 重复直到你和用户都满意
- 打包最终的技能并交还给用户。

如果你有类似待办清单的东西，请把这些步骤加进你的 TodoList，以确保你不会忘记。如果你在 Cowork 中，请特别把 "Create evals JSON and run `eval-viewer/generate_review.py` so human can review test cases" 放进你的 TodoList，以确保它一定会发生。

祝你好运！
