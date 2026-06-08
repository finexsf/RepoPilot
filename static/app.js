let analysisId = null;
let analysis = null;
let pollTimer = null;
let selectedNode = null;
let currentLang = localStorage.getItem("repopilot_lang") || "en";
let chatHistory = [];

const $ = (id) => document.getElementById(id);

const I18N = {
  en: {
    toggle: "中文",
    eyebrow: "AI Software Onboarding Agent",
    subtitle: "AI Software Onboarding Agent for First-time Contributors",
    roleBeginner: "Beginner",
    roleIntermediate: "Intermediate",
    roleAdvanced: "Advanced",
    goalContribute: "First Contribution",
    goalUnderstand: "Understand Project",
    goalRun: "Run Project",
    analyze: "Analyze Repository",
    loadDemo: "Load Demo",
    statusLabel: "Status",
    progressLabel: "Progress",
    agentStepLabel: "Agent Step",
    ready: "Ready",
    initialStep: "Paste a GitHub repository URL and start analysis.",
    tabOverview: "Overview",
    tabArchitecture: "Architecture",
    tabLearning: "Learning Path",
    tabContribution: "Contribution Radar",
    tabTrace: "Agent Trace",
    tabChat: "Agent Chat",
    emptyOverview: "No analysis yet.",
    emptyArchitecture: "Architecture graph will appear here.",
    emptyLearning: "Personalized onboarding path will appear here.",
    emptyContribution: "Contribution radar will appear here.",
    emptyTrace: "Multi-agent trace will appear here.",
    emptyChat: "Ask RepoPilot about this repository.",
    analyzing: "Analyzing repository with Tree-sitter CodeGraph...",
    creatingWorkflow: "Creating multi-agent onboarding workflow.",
    loadingDemo: "Loading the latest completed Tree-sitter CodeGraph analysis.",
    loadedDemo: "Loaded cached demo analysis.",
    analysisFailed: "Analysis failed",
    failureHelp: "You can retry the repository, or click Load Demo to show a stable cached Tree-sitter CodeGraph analysis.",
    files: "Files",
    modules: "Modules",
    relations: "Relations",
    onboardingScore: "Onboarding Score",
    cognitiveSummary: "Project Cognitive Summary",
    threeMinute: "3-minute understanding",
    detectedCommands: "Detected commands",
    newcomerRisks: "Newcomer Risk Signals",
    topEntryFiles: "Top Entry Files",
    architectureMap: "Architecture Map",
    logicalArchitecture: "Logical Architecture",
    moduleCallGraph: "Module Call Graph",
    threeLevelCalls: "Three-level Calls",
    evidenceGraph: "File-level CodeGraph Evidence",
    coreCallChain: "Core Call Chain",
    entryLayer: "Entry Layer",
    coreLayer: "Core Layer",
    supportLayer: "Support Layer",
    coreFlow: "Core Flow",
    inspector: "Node Inspector",
    role: "Role",
    keySymbols: "Key functions/classes",
    imports: "Imports / relations",
    whyRead: "Why newcomers should read it",
    noSymbols: "No top-level symbol detected.",
    noImports: "No direct import edge in current graph.",
    readingReason: "Reading reason",
    checkpoint: "Checkpoint",
    checkpointQuiz: "Checkpoint Quiz",
    expectedAnswer: "Expected answer",
    matrixX: "Difficulty: Beginner -> Advanced",
    matrixY: "Impact",
    firstPrPlan: "First PR Plan",
    input: "Input",
    action: "Action",
    output: "Output",
    nextStep: "Next step",
    confidence: "confidence",
    reflectionAgent: "Reflection Agent",
    limitations: "Limitations",
    recommendedNextInput: "Recommended next input",
    chatTitle: "Ask RepoPilot",
    chatSubtitle: "Ask about architecture, key files, setup, learning path, or first PR strategy.",
    chatPlaceholder: "Ask: Which file should I read first?",
    send: "Send",
    suggestedQuestions: "Suggested questions",
  },
  zh: {
    toggle: "EN",
    eyebrow: "AI 软件上手 Agent",
    subtitle: "面向开源项目新贡献者的 AI Software Onboarding Agent",
    roleBeginner: "新手",
    roleIntermediate: "中级",
    roleAdvanced: "高级",
    goalContribute: "首次贡献",
    goalUnderstand: "理解项目",
    goalRun: "跑通项目",
    analyze: "分析仓库",
    loadDemo: "加载演示",
    statusLabel: "状态",
    progressLabel: "进度",
    agentStepLabel: "Agent 步骤",
    ready: "就绪",
    initialStep: "输入 GitHub 仓库地址后开始分析。",
    tabOverview: "项目总览",
    tabArchitecture: "架构地图",
    tabLearning: "学习路径",
    tabContribution: "贡献雷达",
    tabTrace: "Agent 轨迹",
    tabChat: "Agent 对话",
    emptyOverview: "尚未开始分析。",
    emptyArchitecture: "这里将展示架构图。",
    emptyLearning: "这里将展示个性化学习路径。",
    emptyContribution: "这里将展示贡献任务推荐。",
    emptyTrace: "这里将展示多 Agent 协作轨迹。",
    emptyChat: "在这里向 RepoPilot 询问这个仓库。",
    analyzing: "正在使用 Tree-sitter CodeGraph 分析仓库...",
    creatingWorkflow: "正在创建多 Agent 上手分析流程。",
    loadingDemo: "正在加载最近一次完成的 Tree-sitter CodeGraph 演示分析。",
    loadedDemo: "已加载缓存演示分析。",
    analysisFailed: "分析失败",
    failureHelp: "你可以重试该仓库，或点击“加载演示”展示稳定的缓存分析结果。",
    files: "文件数",
    modules: "模块数",
    relations: "关系数",
    onboardingScore: "上手评分",
    cognitiveSummary: "项目认知摘要",
    threeMinute: "3 分钟理解",
    detectedCommands: "识别到的命令",
    newcomerRisks: "新手风险提示",
    topEntryFiles: "关键入口文件",
    architectureMap: "架构地图",
    logicalArchitecture: "逻辑架构",
    moduleCallGraph: "模块调用图",
    threeLevelCalls: "三级调用关系",
    evidenceGraph: "文件级 CodeGraph 证据",
    coreCallChain: "核心调用链",
    entryLayer: "入口层",
    coreLayer: "核心层",
    supportLayer: "支撑层",
    coreFlow: "核心流程",
    inspector: "节点详情",
    role: "作用",
    keySymbols: "关键函数 / 类",
    imports: "导入 / 关系",
    whyRead: "为什么新手应该读它",
    noSymbols: "未检测到顶层符号。",
    noImports: "当前图中没有直接导入边。",
    readingReason: "阅读原因",
    checkpoint: "检查问题",
    checkpointQuiz: "Checkpoint 小测",
    expectedAnswer: "参考答案",
    matrixX: "难度：新手 -> 高级",
    matrixY: "影响力",
    firstPrPlan: "首次 PR 计划",
    input: "输入",
    action: "动作",
    output: "输出",
    nextStep: "下一步",
    confidence: "置信度",
    reflectionAgent: "Reflection Agent 反思",
    limitations: "本次分析不足",
    recommendedNextInput: "建议下一步补充",
    chatTitle: "询问 RepoPilot",
    chatSubtitle: "可以询问架构、关键文件、环境搭建、学习路径或首次 PR 策略。",
    chatPlaceholder: "例如：我应该先读哪个文件？",
    send: "发送",
    suggestedQuestions: "推荐问题",
  },
};

function t(key) {
  return (I18N[currentLang] && I18N[currentLang][key]) || I18N.en[key] || key;
}

const ZH_EXACT = {
  "deterministic fallback": "确定性兜底",
  disabled: "未启用",
  completed: "已完成",
  analyzing: "分析中",
  pending: "排队中",
  failed: "失败",
  entry: "入口",
  module: "模块",
  utility: "工具",
  source: "源码",
  docs: "文档",
  config: "配置",
  ci: "CI",
  test: "测试",
  domain: "领域",
  runtime: "运行时",
  service: "服务",
  integration: "集成",
  ui: "界面",
  uses: "使用",
  imports: "导入",
  calls: "调用",
  initializes: "初始化",
  dispatches: "分发",
  documents: "文档说明",
  Beginner: "新手",
  Intermediate: "中级",
  Advanced: "高级",
  "GitHub Issue": "GitHub Issue",
  "Simulated static-analysis opportunity": "静态分析模拟机会",
  "DeepSeek reasoning over GitHub Issues and static CodeGraph": "DeepSeek 基于 GitHub Issues 和静态 CodeGraph 推理",
  "No top-level symbol detected.": "未检测到顶层符号。",
  "No direct import edge in current graph.": "当前图中没有直接导入边。",
  "Development Workflow": "开发流程",
  "Analysis completed": "分析完成",
  "Analysis failed.": "分析失败。",
  "Parsing GitHub URL": "解析 GitHub URL",
  "Fetching GitHub metadata": "获取 GitHub 元数据",
  "Downloading repository snapshot": "下载仓库快照",
  "Building repository profile": "构建仓库画像",
  "Parsing code with Tree-sitter and building CodeGraph": "使用 Tree-sitter 解析代码并构建 CodeGraph",
  "Enhancing onboarding analysis with DeepSeek": "使用 DeepSeek 增强上手分析",
  "Generating learning paths": "生成学习路径",
  "Mining newcomer-friendly issues": "挖掘适合新手的 Issue",
  "Running full-process DeepSeek reasoning": "运行 DeepSeek 全流程推理",
  "Orchestrator Agent": "Orchestrator Agent 编排代理",
  "Repo Scanner Agent": "Repo Scanner Agent 仓库扫描代理",
  "CodeGraph Agent": "CodeGraph Agent 代码图谱代理",
  "Onboarding Planner Agent": "Onboarding Planner Agent 上手规划代理",
  "Contribution Advisor Agent": "Contribution Advisor Agent 贡献顾问代理",
  "Reflection Agent": "Reflection Agent 反思代理",
  "DeepSeek Reasoning Agent": "DeepSeek Reasoning Agent 推理代理",
  "GitHub Integration Layer": "GitHub 集成层",
  "Issue Miner Agent": "Issue Miner Agent 任务挖掘代理",
  "Architecture Agent": "Architecture Agent 架构代理",
  "Learning Coach Agent": "Learning Coach Agent 学习教练代理",
  "Repository snapshot and metadata": "仓库快照和元数据",
  "Source files and Tree-sitter AST": "源码文件和 Tree-sitter AST",
  "Role, goal, important files": "用户角色、目标和关键文件",
  "Issues or simulated opportunities": "Issue 或模拟贡献机会",
  "All analysis artifacts": "全部分析产物",
  "Show dashboard": "展示 Dashboard",
  "Build repository profile": "构建仓库画像",
  "Rank entry files": "排序入口文件",
  "Guide user reading": "引导用户阅读",
  "Choose a first contribution": "选择首次贡献任务",
  "Ask user to run/test locally": "建议用户本地运行/测试",
  "Clone repository": "克隆仓库",
  "Create environment": "创建运行环境",
  "Install dependencies": "安装依赖",
  "Run project or demo": "运行项目或 Demo",
  "Validate before PR": "提交 PR 前验证",
  "Inference / Quick Start": "推理 / 快速开始",
  "Demo / Basic Demo": "演示 / 基础 Demo",
  "Demo / Real-Time Interactive Demo": "演示 / 实时交互 Demo",
  "Web / Interactive Demo": "Web / 交互式 Demo",
  "Core Model / API": "核心模型 / API",
  "Tests / Evaluation": "测试 / 评测",
  "Documentation / Examples": "文档 / 示例",
  "Project Showcase": "项目展示",
  "Repository demo media": "仓库演示媒体",
  "User Entry / Demo": "用户入口 / Demo",
  "Application / Demo Layer": "应用 / Demo 层",
  "Core Domain Modules": "核心领域模块",
  "Runtime Services": "运行时服务",
  "Platform / Drivers": "平台 / 驱动",
  "Shared Libraries / Tools": "共享库 / 工具",
  "Config / Build": "配置 / 构建",
  "Tests / Validation": "测试 / 验证",
  "Docs / Examples": "文档 / 示例",
  "Logical Architecture & Module Calls": "逻辑架构与模块调用",
  "Module-level graph aggregated from Tree-sitter symbols, imports, file roles, and CodeGraph edges.": "基于 Tree-sitter 符号、import、文件职责和 CodeGraph 边聚合得到的模块级图。",
  "local cache": "本地缓存",
  "downloaded snapshot": "下载快照",
  "deterministic fallback": "确定性兜底",
};

function localize(value) {
  if (value === null || value === undefined) return "";
  let text = String(value);
  if (currentLang !== "zh" || !text) return text;
  if (/[\u4e00-\u9fff]/.test(text)) return text;
  if (ZH_EXACT[text]) return ZH_EXACT[text];
  if (text.startsWith("RAGFlow is a leading open-source Retrieval-Augmented Generation")) {
    return "RAGFlow 是一个领先的开源 Retrieval-Augmented Generation (RAG) 引擎，将先进的 RAG 能力与 Agent 能力结合，为 LLM 应用构建更强的上下文层。";
  }
  if (text.startsWith("RAGFlow is an open-source RAG engine that combines retrieval-augmented generation")) {
    return "RAGFlow 是一个开源 RAG 引擎，将 Retrieval-Augmented Generation 与 Agent 能力结合起来，帮助企业构建可用于生产环境的 AI 系统。它的核心能力包括深度文档理解、基于模板的 chunking、带引用依据的回答，以及对多种数据源的支持。项目维护活跃，并持续支持 DeepSeek、GPT 等新模型以及 Confluence、Google Drive 等平台集成。新手可以先通过云服务快速体验，也可以使用 Docker 自托管运行。";
  }
  if (text.startsWith("Flask is a lightweight WSGI web application framework")) {
    return "Flask 是一个轻量级 WSGI Web 应用框架，适合快速开始，也可以逐步扩展到复杂应用。";
  }
  if (text.startsWith("Flask is a popular Python web framework")) {
    return "Flask 是一个流行的 Python Web 框架，用简单灵活的方式构建 Web 应用。它基于 Werkzeug 和 Jinja，不强制特定依赖或项目结构。新手可以从 README、测试目录和核心 Flask 类开始理解请求响应流程，再选择文档或测试类的小任务作为首次 PR。";
  }
  if (text.startsWith("Home Assistant is an open-source home automation platform")) {
    return "Home Assistant 是一个开源的智能家居自动化平台，基于 Python 运行，强调本地控制和隐私保护。";
  }
  if (text.startsWith("Home Assistant is a home automation platform")) {
    return "Home Assistant 是一个智能家居自动化平台，用于控制和联动各种智能设备。它在本地运行，优先保护隐私。核心后端由 Python 编写，仓库中包含 `homeassistant/` 后端逻辑、配置文件和贡献文档。关键代码包括 `core.py` 事件系统、`config_entries.py` 集成配置管理、`bootstrap.py` 启动流程。项目使用 pytest 进行测试。新手可以先理解事件驱动架构，再学习 integration 如何注册实体和服务。";
  }
  if (text.startsWith("VITA is an open-source interactive multimodal LLM")) {
    return "VITA 是一个开源交互式 Multimodal LLM 项目，核心目标是支持图像、视频、语音和文本的实时交互。上手时应先跑通 Inference / Quick Start，再分别复现 Basic Demo 和 Real-Time Interactive Demo，最后从 web_demo、video_audio_demo.py 或模型配置相关文件切入修改。";
  }
  if (text.startsWith("VITA-1.5 supports both English and Chinese")) {
    return "VITA-1.5 支持英文和中文交互，README 中的核心复现入口集中在 Inference 章节，包括 Quick Start、Basic Demo 和 Real-Time Interactive Demo。";
  }
  if (text.startsWith("The architecture centers on VITA")) {
    return "该项目架构围绕 VITA 多模态模型展开：推理入口负责加载模型和输入样例，web_demo 提供基础与实时交互 demo，模型目录负责语言模型、多模态融合和音视频处理。";
  }
  if (text.startsWith("Start from the Inference section")) {
    return "建议先从 README 的 Inference 章节开始，依次复现 Quick Start、Basic Demo 和 Real-Time Interactive Demo，再阅读对应入口文件。";
  }
  if (text.startsWith("The architecture is event-driven.")) {
    return "该项目是事件驱动架构。`core.py` 管理状态和事件，`homeassistant/components/` 中的 integrations 注册实体和服务，`config_entries.py` 处理配置流程，`bootstrap.py` 负责系统启动。建议先读 `core.py`、`config_entries.py`，再挑一个简单 integration 理解完整链路。";
  }
  if (text.startsWith("As an intermediate developer")) {
    return "作为中级开发者，建议重点理解事件系统和 integration 工作方式。先阅读 `core.py` 与 `config_entries.py`，再查看一个简单 integration 如何注册实体。用 pytest 运行测试，理解项目的测试模式。";
  }
  if (text.startsWith("For your first PR")) {
    return "首次 PR 建议寻找 `good first issue` 或 `help wanted` 标签任务。常见切入点包括补充测试、改进文档、修复小 bug。先搭建开发环境、运行测试，再提交一个范围清晰的小改动。";
  }
  text = text
    .replace("Get a local copy before reading or modifying code.", "在阅读或修改代码前，先把仓库克隆到本地。")
    .replace("Create or enter the runtime environment described by README.", "创建或进入 README 中要求的运行环境。")
    .replace("Use this to verify the runtime path before changing source code.", "修改源码前先用该命令验证运行链路。")
    .replace("Detected from setup files:", "根据依赖/配置文件识别：")
    .replace("Detected test evidence:", "根据测试证据识别：")
    .replace("Run the repository's user-facing demo or web interface.", "运行仓库面向用户的 Demo 或 Web 界面。")
    .replace("Read the central model or API modules before attempting source changes.", "修改源码前先阅读核心模型或 API 模块。")
    .replace("Validate a first PR with tests or evaluation scripts.", "用测试或评测脚本验证首次 PR。")
    .replace("Find the safest documentation or example contribution surface.", "寻找最安全的文档或示例贡献入口。")
    .replace("Run single-turn VITA inference for text, image, and audio examples from README.", "运行 README 中的 VITA 单轮推理示例，覆盖文本、图像和音频输入。")
    .replace("Launch the basic VITA web ability demo after preparing the vLLM-adapted demo checkpoint.", "准备好 vLLM 适配后的 demo checkpoint 后，启动 VITA 基础 Web Demo。")
    .replace("Start the real-time interactive VITA server with VAD resources and the demo checkpoint.", "准备 VAD 资源和 demo checkpoint 后，启动 VITA 实时交互服务。")
    .replace("Dependency installation command is not explicit; confirm package manager and Python/Node version before reproducing.", "依赖安装命令不够明确；复现前需要确认包管理器以及 Python/Node 版本。")
    .replace("No direct demo/service command was detected; reproduction may require locating the runtime entry or release artifact first.", "未识别到可直接运行的 demo / 服务命令；复现前可能需要先定位运行入口或 Release 产物。")
    .replace("Validation command is not explicit; run a small smoke test before changing source code.", "验证命令不够明确；修改源码前应先跑一个最小冒烟测试。")
    .replace("Static import graph is sparse; runtime wiring may be hidden in configuration, plugin registration, or dynamic imports.", "静态 import 图较稀疏；真实运行链路可能隐藏在配置、插件注册或动态导入中。")
    .replace("GitHub issues were unavailable; first-contribution opportunities are inferred from static analysis rather than maintainer labels.", "GitHub Issues 不可用；首次贡献机会来自静态分析推断，而不是维护者标签。")
    .replace("Reproduce the project before editing: install dependencies, run one demo/service command, then validate with the detected test command.", "修改前先复现项目：安装依赖、运行一个 demo / 服务命令，再用识别到的测试命令验证。")
    .replace("No complete install command was detected; confirm the dependency manager before reproducing.", "未检测到完整安装命令；复现前先确认依赖管理方式。")
    .replace("No direct demo/service command was detected; locate entry files or release usage first.", "未检测到直接可运行的 demo / 服务命令；请先定位入口文件或 Release 使用方式。")
    .replace("Run setup first, then edit Top Entry Files; avoid broad core changes in the first pass.", "先跑通环境，再修改 Top Entry Files；首次修改避免大范围触碰核心逻辑。")
    .replace("First contribution task", "首次贡献任务")
    .replace("First contribution advice", "首次贡献建议")
    .replace("Recommended tasks", "推荐任务")
    .replace("Prefer low-risk, verifiable tasks with a small file scope.", "优先选择低风险、可验证、涉及文件少的小任务。")
    .replace("Ask about setup, files, architecture, or first PR strategy.", "可以继续询问环境搭建、关键文件、架构或首次 PR 策略。")
    .replace("No direct runnable commands were detected.", "未识别到可直接执行的命令。")
    .replace("Use these commands to reproduce the project:", "按这些命令复现项目：")
    .replace("Follow this learning path:", "按这个学习路径推进：")
    .replace("Read the architecture as:", "可以这样理解架构：")
    .replace("Map architecture layers", "梳理架构分层")
    .replace("Separate entry, module, and utility surfaces.", "区分入口、核心模块和工具支撑层。")
    .replace("Read configuration and runtime wiring", "阅读配置与运行时连接")
    .replace("Connect setup/config files with source modules.", "把 setup/config 文件与源码模块连接起来理解。")
    .replace("Understand test strategy", "理解测试策略")
    .replace("Find smallest validation path for a change.", "找到一次改动最小可行的验证路径。")
    .replace("Pick a bounded contribution", "选择边界清晰的贡献任务")
    .replace("Choose a task with clear files and verification.", "选择文件范围和验证方式都清楚的任务。")
    .replace("Explain back the architecture", "复述项目架构")
    .replace("Summarize entry, core module, utility, and test surfaces.", "总结入口、核心模块、工具模块和测试入口。")
    .replace("Which files form the backbone?", "哪些文件构成项目主干？")
    .replace("Which config affects runtime behavior?", "哪些配置会影响运行时行为？")
    .replace("Which test should run before a PR?", "提交 PR 前应该运行哪个测试？")
    .replace("What is the smallest reviewable diff?", "最小且可 review 的 diff 是什么？")
    .replace("Can you explain the project in 3 minutes?", "你能在 3 分钟内讲清楚这个项目吗？")
    .replace("Selected from README, entry-file heuristics, and CodeGraph importance.", "由 DeepSeek 结合 README、入口文件启发式规则和 CodeGraph 重要性选择。")
    .replace("Read README and contribution documents before editing.", "修改前先阅读 README 和贡献文档。")
    .replace("Keep the first PR focused on one small behavior, test, example, or documentation change.", "首次 PR 聚焦一个小行为、测试、示例或文档改动。")
    .replace("Run the detected validation command before submitting.", "提交前运行识别到的验证命令。")
    .replace("Reference the related issue or explain the static-analysis opportunity.", "关联相关 issue，或说明该静态分析机会的来源。")
    .replace("Include changed files, test result, and before/after behavior in the PR description.", "在 PR 描述中写清修改文件、测试结果和改动前后行为。")
    .replace("Prefer nearby code style over broad refactors.", "优先遵循附近代码风格，不做大范围重构。")
    .replace("Add or update tests when behavior changes.", "行为变化时添加或更新测试。")
    .replace("Avoid touching unrelated modules in a first contribution.", "首次贡献避免触碰无关模块。")
    .replace("Use CI/config files as the source of truth for project validation.", "以 CI/config 文件作为验证方式的依据。")
    .replace("Static analysis based on Tree-sitter AST and imports, with DeepSeek reasoning over the CodeGraph.", "基于 Tree-sitter AST 和 imports 的静态分析，并由 DeepSeek 对 CodeGraph 进行推理。")
    .replace("Static analysis based on Tree-sitter AST, imports, and deterministic CodeGraph heuristics.", "基于 Tree-sitter AST、imports 和确定性 CodeGraph 启发式规则的静态分析。")
    .replace("Static entry flow is sparse; start from README and the highest-ranked core module.", "静态入口链路较稀疏，建议从 README 和最高分核心模块开始。")
    .replace("Project Position", "项目定位")
    .replace("Architecture Reading", "架构阅读")
    .replace("Learning Route", "学习路线")
    .replace("First PR Focus", "首次 PR 焦点")
    .replace("semantic layers", "个语义架构层")
    .replace("guided steps", "个引导步骤")
    .replace("Derived from DeepSeek's README-grounded repository positioning.", "来自 DeepSeek 基于 README 的项目定位判断。")
    .replace("DeepSeek reconstructed the architecture from CodeGraph evidence.", "DeepSeek 基于 CodeGraph 证据重建了项目架构。")
    .replace("DeepSeek generated a role-aware route with files, reasons, and checkpoints.", "DeepSeek 生成了包含文件、阅读原因和检查点的角色化学习路线。")
    .replace("DeepSeek ranked contribution tasks by newcomer fit, impact, and risk.", "DeepSeek 按新手适配度、影响力和风险对贡献任务排序。")
    .replace("Selected by DeepSeek from Tree-sitter CodeGraph evidence.", "由 DeepSeek 根据 Tree-sitter CodeGraph 证据选择。")
    .replace("Generated by DeepSeek from README and CodeGraph evidence.", "由 DeepSeek 根据 README 和 CodeGraph 证据生成。")
    .replace("This layer helps newcomers connect the project goal to concrete code.", "这一层帮助新手把项目目标连接到具体代码。")
    .replace("Architecture layer inferred by DeepSeek from CodeGraph evidence.", "DeepSeek 根据 CodeGraph 证据推断出的架构层。")
    .replace("Confirm scope before editing.", "修改前请先确认变更范围。")
    .replace("Low blast radius; suitable for a first contribution sandbox.", "影响范围较小，适合作为首次贡献练习。")
    .replace("Scope may be larger than it looks; verify behavior with tests.", "实际范围可能比表面更大，请用测试验证行为。")
    .replace("Read the recommended files and restate the change scope.", "阅读推荐文件，并用自己的话复述变更范围。")
    .replace("Make one small documentation/test/config/source change.", "只做一个小的文档、测试、配置或源码变更。")
    .replace("Run the detected validation command and open a focused PR.", "运行识别到的验证命令，并提交聚焦的 PR。")
    .replace("Run the install/test command locally and paste failures back into RepoPilot.", "在本地运行安装/测试命令，并把失败信息反馈给 RepoPilot。")
    .replace("Choose one contribution task and inspect the recommended files.", "选择一个贡献任务，并查看推荐文件。")
    .replace("If available, provide a GitHub token to improve Issue and PR analysis.", "如有 GitHub token，可提供以提升 Issue 和 PR 分析质量。");
  text = text.replace(/^Tree-sitter parsed ([a-zA-Z]+) file\. Key symbols: (.*)\. Imports: (.*)\.$/, (_, lang, symbols, imports) => `Tree-sitter 解析的 ${lang} 文件。关键符号：${symbols}。导入：${imports}。`);
  text = text.replace(/^It is likely to be an onboarding entry because it is documentation, configuration, or a runtime entry file\.$/, "它很可能是上手入口，因为它是文档、配置或运行时入口文件。");
  text = text.replace(/^It connects to (\d+) CodeGraph relations and gives newcomers a high-leverage view of project behavior\.$/, "它连接了 $1 条 CodeGraph 关系，能让新手高效理解项目行为。");
  text = text.replace(/^It is a bounded utility surface; useful after reading the main flow\.$/, "它是边界较清晰的工具模块，适合在读完主流程后查看。");
  text = text.replace(/^(.+) depends on (.+) through static (.+) analysis\.$/, "$1 通过静态 $3 分析依赖 $2。");
  text = text.replace(/^Add or refine a small test near (.+)$/, "在 $1 附近补充或优化一个小测试");
  text = text.replace(/^Create a first-contribution reading note for (.+)$/, "为 $1 编写首次贡献阅读笔记");
  text = text.replace(/^Improve documentation around (.+)$/, "改进 $1 相关文档");
  text = text.replace(/^Refactor a bounded utility near (.+)$/, "重构 $1 附近的边界清晰工具逻辑");
  text = text.replace(/^Add an example demo for (.+)$/, "为 $1 增加示例 Demo");
  text = text.replace(/^Fix config validation around (.+)$/, "修复 $1 相关配置校验");
  text = text.replace(/^Simulated static-analysis opportunity$/, "静态分析模拟机会");
  text = text.replace(/^has newcomer-friendly labels; (.+)$/i, "具备新手友好信号；$1");
  text = text.replace(/^mentions likely related modules: (.+)$/i, "提到了可能相关的模块：$1");
  text = text.replace(/^appears to have a focused change scope; has a clear verification path$/i, "变更范围较聚焦，并且有较清晰的验证路径");
  text = text.replace(/^documentation convention$/, "文档约定");
  text = text.replace(/^test layout$/, "测试布局");
  text = text.replace(/^core module API$/, "核心模块 API");
  text = text.replace(/^configuration surface$/, "配置入口");
  text = text.replace(/^Scanned (\d+) files$/, "扫描了 $1 个文件");
  text = text.replace(/^(\d+) nodes, (\d+) relations$/, "$1 个节点，$2 条关系");
  text = text.replace(/^Analysis state: (.+)$/, "分析状态：$1");
  return text;
}

function htmlText(value, options = {}) {
  const text = cleanUiText(localize(value));
  if (!options.preserveMixedTechnicalText && currentLang === "zh" && isMostlyEnglish(text)) {
    return escapeHtml(genericZhFallback(text));
  }
  return escapeHtml(text);
}

function isMostlyEnglish(value) {
  const text = String(value || "");
  const latin = (text.match(/[A-Za-z]/g) || []).length;
  const cjk = (text.match(/[\u4e00-\u9fff]/g) || []).length;
  return latin > 40 && cjk < latin * 0.25;
}

function localizedAdvice(profile, field) {
  const value = profile?.[field] || "";
  if (currentLang !== "zh") return value;
  const translated = cleanUiText(localize(value));
  return /[\u4e00-\u9fff]/.test(translated) ? translated : "";
}

function genericZhFallback(text) {
  if (/demo|run|server|inference|quick start/i.test(text)) {
    return "项目运行或 Demo 复现入口：按下方命令执行，并打开关联文件查看入口逻辑。";
  }
  if (/test|validation|pytest|evaluate|benchmark/i.test(text)) {
    return "测试或评测验证入口：执行下方验证命令，并打开关联文件查看断言范围。";
  }
  if (/architecture|module|codegraph|import|dependency/i.test(text)) {
    return "RepoPilot 已读取模块图、文件边和函数调用样例；请查看下方具体模块、文件和调用证据。";
  }
  if (/contribution|issue|pr|change|scope/i.test(text)) {
    return "首次贡献任务：先打开推荐文件，限定变更范围，再执行验证步骤。";
  }
  return "基于当前仓库的文件、命令和调用关系生成。";
}

function cleanUiText(value) {
  if (value === null || value === undefined) return "";
  return String(value)
    .replace(/[‘’]/g, "'")
    .replace(/\s+'/g, " ")
    .replace(/'\s+/g, " ")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/\bSee README\b/gi, currentLang === "zh" ? "未识别到可直接执行命令" : "No direct runnable command detected")
    .replace(/\s{2,}/g, " ")
    .trim();
}

function sentenceCards(text, limit = 4) {
  const cleaned = cleanUiText(text);
  if (!cleaned) return [];
  return cleaned
    .split(/(?<=[。！？!?])\s+|(?<=\.)\s+(?=[A-Z])|\n+/)
    .map((item) => item.trim())
    .filter(Boolean)
    .slice(0, limit);
}

function isUsefulCommand(command) {
  const text = String(command || "").trim();
  if (!text) return false;
  const lower = text.toLowerCase();
  if (["see readme", "read readme", "pytest", "npm test"].includes(lower)) return false;
  if (lower.includes("<changed_module_or_package>")) return false;
  return true;
}

function localizedField(object, field) {
  if (!object) return "";
  if (currentLang === "zh") {
    const zhValue = object[`zh_${field}`];
    if (zhValue && !isMostlyEnglish(zhValue)) return zhValue;
  }
  const value = object[field] || "";
  if (currentLang === "zh" && isMostlyEnglish(value)) {
    if (field === "one_liner") {
      return object.name
        ? `${object.name} 是一个需要结合 README、关键入口文件和 CodeGraph 来理解的开源项目。`
        : "这是一个需要结合 README、关键入口文件和 CodeGraph 来理解的开源项目。";
    }
    if (field === "cognitive_summary") {
      return object.name
        ? `${object.name} 的上手路径应围绕三个目标展开：先理解项目定位和核心模块，再按环境步骤复现 demo，最后从影响范围较小的文件开始做首次修改。`
        : "建议先理解项目定位和核心模块，再按环境步骤复现 demo，最后从影响范围较小的文件开始做首次修改。";
    }
  }
  return value;
}

function localizeDifficulty(value) {
  return currentLang === "zh" ? (ZH_EXACT[value] || value) : value;
}

async function applyLanguage() {
  document.documentElement.lang = currentLang === "zh" ? "zh-CN" : "en";
  $("langToggle").textContent = t("toggle");
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    node.textContent = t(node.dataset.i18n);
  });
  if (analysis) {
    if (analysisId) {
      try {
        analysis = await getJson(`/api/analysis/${analysisId}?lang=${currentLang}`);
      } catch (error) {
        console.warn("Failed to reload translated analysis", error);
      }
    }
    $("status").textContent = localize(analysis.status || "completed");
    $("currentStep").textContent = localize(analysis.current_step || t("loadedDemo"));
    renderDashboard();
  }
}

$("langToggle").addEventListener("click", () => {
  currentLang = currentLang === "en" ? "zh" : "en";
  localStorage.setItem("repopilot_lang", currentLang);
  applyLanguage();
});

applyLanguage();

document.querySelectorAll(".tab").forEach((button) => {
  button.addEventListener("click", () => activateTab(button.dataset.tab));
});

document.addEventListener("click", (event) => {
  const chip = event.target.closest(".file-chip");
  if (!chip || !chip.dataset.file) return;
  event.preventDefault();
  openFilePreview(chip.dataset.file);
});

function activateTab(name) {
  document.querySelectorAll(".tab").forEach((tab) => tab.classList.toggle("active", tab.dataset.tab === name));
  document.querySelectorAll(".tab-page").forEach((page) => page.classList.remove("active"));
  $(`${name}Tab`).classList.add("active");
}

$("repoForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  resetDashboard();
  const payload = {
    url: $("repoUrl").value.trim(),
    user_profile: $("userRole").value,
    goal: $("goal").value,
  };
  const response = await postJson("/api/analyze", payload);
  analysisId = response.analysis_id;
  startPolling();
});

$("loadDemo").addEventListener("click", async () => {
  resetDashboard();
  $("status").textContent = currentLang === "zh" ? "加载演示中" : "loading cached demo";
  $("currentStep").textContent = t("loadingDemo");
  analysis = await getJson(`/api/demo-analysis?lang=${currentLang}`);
  analysisId = analysis.id;
  $("status").textContent = localize(analysis.status || "completed");
  $("progress").textContent = `${analysis.progress || 100}%`;
  $("currentStep").textContent = t("loadedDemo");
  renderDashboard();
});

function resetDashboard() {
  analysis = null;
  selectedNode = null;
  chatHistory = [];
  $("status").textContent = currentLang === "zh" ? "分析中" : "analyzing";
  $("progress").textContent = "0%";
  $("currentStep").textContent = t("creatingWorkflow");
  ["overviewPage", "architecturePage", "learningPage", "contributionPage", "tracePage", "chatPage"].forEach((id) => {
    $(id).className = "empty-state";
    $(id).innerHTML = t("analyzing");
  });
}

function startPolling() {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(refreshAnalysis, 1100);
}

async function refreshAnalysis() {
  if (!analysisId) return;
  const data = await getJson(`/api/analysis/${analysisId}?lang=${currentLang}`);
  $("status").textContent = localize(data.status || "unknown");
  $("progress").textContent = `${data.progress || 0}%`;
  $("currentStep").textContent = localize(data.current_step || "-");
  if (data.status === "completed") {
    clearInterval(pollTimer);
    analysis = data;
    renderDashboard();
  }
  if (data.status === "failed") {
    clearInterval(pollTimer);
    $("currentStep").textContent = localize(data.error || "Analysis failed.");
    renderFailure(data.error || t("analysisFailed"));
  }
}

function renderFailure(message) {
  const html = `
    <div class="failure-card">
      <h2>${t("analysisFailed")}</h2>
      <p>${htmlText(message)}</p>
      <p class="muted">${t("failureHelp")}</p>
    </div>
  `;
  ["overviewPage", "architecturePage", "learningPage", "contributionPage", "tracePage"].forEach((id) => {
    $(id).className = "";
    $(id).innerHTML = html;
  });
}

function renderDashboard() {
  renderOverview();
  renderArchitecture();
  renderLearning();
  renderContribution();
  renderTrace();
  renderChat();
}

function renderOverview() {
  const profile = analysis.repo_profile;
  const metrics = analysis.metrics;
  const important = analysis.important_files || [];
  const summaryCards = sentenceCards(localizedField(profile, "cognitive_summary"), 3);
  const risks = ((currentLang === "zh" && profile.zh_risks && profile.zh_risks.length ? profile.zh_risks : profile.risks) || []);
  const adviceItems = ["architecture_insight", "learning_advice", "contribution_advice"]
    .map((field) => localizedAdvice(profile, field))
    .filter(Boolean);
  const target = $("overviewPage");
  target.className = "";
  target.innerHTML = `
    <div class="metric-grid">
      ${metricCard(t("files"), metrics.files)}
      ${metricCard(t("modules"), metrics.modules)}
      ${metricCard(t("relations"), metrics.relations)}
      ${metricCard(t("onboardingScore"), metrics.onboarding_score)}
    </div>
    ${renderOverviewCards(profile.overview_cards || [])}
    <div class="overview-layout">
      <section class="panel">
        <h2>${currentLang === "zh" ? "项目认知摘要" : "Project Cognitive Summary"}</h2>
        <p class="summary-copy">${htmlText(localizedField(profile, "one_liner"))}</p>
        <div class="summary-card-grid">
          <article class="summary-card">
            <span class="label">${currentLang === "zh" ? "理解工程" : "Understand"}</span>
            <p>${htmlText(summaryCards[0] || localizedField(profile, "one_liner"))}</p>
          </article>
          <article class="summary-card">
            <span class="label">${currentLang === "zh" ? "复现重点" : "Reproduce"}</span>
            <p>${htmlText((profile.setup_guide || []).find((step) => (step.commands || []).some(isUsefulCommand))?.reason || risks[0] || (currentLang === "zh" ? "先完成环境搭建，再运行明确 demo 命令。" : "Set up the environment, then run an explicit demo command."))}</p>
          </article>
          <article class="summary-card">
            <span class="label">${currentLang === "zh" ? "修改入口" : "Modify"}</span>
            <p>${htmlText((important[0]?.why_important || "") + (important[0]?.path ? ` ${important[0].path}` : ""))}</p>
          </article>
        </div>
        ${adviceItems.length ? `
          <div class="inspector-section">
            <span class="label">${currentLang === "zh" ? "DeepSeek Agent 建议" : "DeepSeek Agent Advice"}</span>
            ${adviceItems.map((item) => `<p>${htmlText(item)}</p>`).join("")}
          </div>
        ` : ""}
      </section>
      <section class="panel">
        <h2>${currentLang === "zh" ? "复现风险与注意事项" : "Reproduction Risk Signals"}</h2>
        <ul class="risk-list">${normalizeRisks(risks, profile).map((risk) => `<li>${htmlText(risk)}</li>`).join("")}</ul>
      </section>
      ${renderSetupGuide(profile.setup_guide || [])}
      ${renderFeatureRunbook(profile.feature_runbook || [])}
      ${renderWorkflowGuide(profile.workflow_guide || {})}
      <section class="panel entry-list">
        <h2>${t("topEntryFiles")}</h2>
        ${important.slice(0, 5).map((file) => `
          <article class="entry-item">
            <div>
              ${fileButton(file.path, file.path)}
              <p>${htmlText(file.why_important)}</p>
              <div class="pill-row">
                <span class="pill">${htmlText(file.category)}</span>
                <span class="pill">${htmlText(file.type)}</span>
              </div>
            </div>
            <div class="score-badge">${file.importance_score}</div>
          </article>
        `).join("")}
      </section>
    </div>
  `;
}

function renderOverviewCards(cards) {
  if (!cards.length) return "";
  return `
    <section class="deepseek-cards">
      <div class="section-heading">
        <div>
          <span class="label">${currentLang === "zh" ? "DeepSeek 项目判断" : "DeepSeek Project Judgement"}</span>
          <h2>${currentLang === "zh" ? "面向新贡献者的关键判断" : "Key Judgements for New Contributors"}</h2>
        </div>
      </div>
      <div class="deepseek-card-grid">
        ${cards.map((card) => `
          <article class="deepseek-card">
            <span class="label">${htmlText(card.label)}</span>
            <strong>${htmlText(card.value)}</strong>
            <p>${htmlText(card.explanation || "")}</p>
          </article>
        `).join("")}
      </div>
    </section>
  `;
}

function normalizeRisks(risks, profile) {
  const cleaned = (risks || [])
    .map((risk) => cleanUiText(localize(risk)))
    .filter(Boolean)
    .filter((risk) => !/no major onboarding blocker|start from readme|未发现明显风险/i.test(risk));
  if (cleaned.length) return cleaned.slice(0, 5);
  const setupCommands = (profile.setup_guide || []).flatMap((step) => step.commands || []).filter(isUsefulCommand);
  const runCommands = (profile.feature_runbook || []).flatMap((feature) => feature.commands || []).filter(isUsefulCommand);
  const fallback = [];
  if (!setupCommands.length) {
    fallback.push(currentLang === "zh" ? "未从 README 或配置文件中提取到完整安装命令，复现前需要先确认依赖管理方式。" : "No complete install command was detected; confirm the dependency manager before reproducing.");
  }
  if (!runCommands.length) {
    fallback.push(currentLang === "zh" ? "未识别到可直接启动的 demo / 服务命令，建议先定位入口文件或 Release 运行方式。" : "No direct demo/service command was detected; locate entry files or release usage first.");
  }
  fallback.push(currentLang === "zh" ? "先按环境搭建步骤跑通，再改动 Top Entry Files；不要一开始修改跨模块核心逻辑。" : "Run setup first, then edit Top Entry Files; avoid broad core changes in the first pass.");
  return fallback.slice(0, 5);
}

function renderWorkflowGuide(workflow) {
  if (!workflow || !workflow.title) return "";
  return `
    <section class="panel entry-list">
      <h2>${currentLang === "zh" ? "开发流程与代码规范" : "Development Workflow & Code Standards"}</h2>
      <div class="workflow-layout">
        <div>
          <span class="label">${currentLang === "zh" ? "验证命令" : "Validation commands"}</span>
          ${renderCommandBlock(workflow.commands || [])}
          <span class="label">${currentLang === "zh" ? "证据文件" : "Evidence files"}</span>
          <div class="pill-row">${(workflow.evidence_files || []).map((file) => fileButton(file, shortName(file, 34))).join("")}</div>
        </div>
        <div>
          <span class="label">${currentLang === "zh" ? "首次 PR Checklist" : "First PR Checklist"}</span>
          <ul class="check-list">${(workflow.checklist || []).map((item) => `<li>${htmlText(item)}</li>`).join("")}</ul>
        </div>
        <div>
          <span class="label">${currentLang === "zh" ? "代码规范推断" : "Code-standard inference"}</span>
          <ul class="check-list">${(workflow.standards || []).map((item) => `<li>${htmlText(item)}</li>`).join("")}</ul>
        </div>
      </div>
    </section>
  `;
}

function renderRequirementCoverage(items) {
  if (!items.length) return "";
  return `
    <section class="panel entry-list">
      <h2>${currentLang === "zh" ? "任务要求覆盖自查" : "Task Requirement Coverage"}</h2>
      <div class="coverage-grid">
        ${items.map((item, index) => `
          <article class="coverage-card">
            <div class="step-index">${index + 1}</div>
            <h3>${htmlText(item.requirement)}</h3>
            <p>${htmlText(item.implementation)}</p>
          </article>
        `).join("")}
      </div>
    </section>
  `;
}

function renderSetupGuide(steps) {
  const runnableSteps = (steps || [])
    .map((step) => ({ ...step, commands: (step.commands || [step.command]).filter(isUsefulCommand) }))
    .filter((step) => step.commands.length);
  if (!runnableSteps.length) return "";
  return `
    <section class="panel entry-list">
      <h2>${currentLang === "zh" ? "环境搭建步骤" : "Environment Setup Steps"}</h2>
      <div class="runbook-grid">
        ${runnableSteps.map((step, index) => `
          <article class="runbook-card">
            <div class="step-index">${index + 1}</div>
            <h3>${htmlText(step.title)}</h3>
            ${renderCommandBlock(step.commands)}
            <p class="muted">${htmlText(step.reason)}</p>
          </article>
        `).join("")}
      </div>
    </section>
  `;
}

function renderFeatureRunbook(features) {
  const runnableFeatures = (features || [])
    .map((feature) => ({ ...feature, commands: (feature.commands || [feature.command]).filter(isUsefulCommand) }))
    .filter((feature) => feature.commands.length);
  if (!runnableFeatures.length) return "";
  return `
    <section class="panel entry-list">
      <h2>${currentLang === "zh" ? "不同功能代码的运行方式" : "How to Run Different Functional Areas"}</h2>
      <p class="muted">${currentLang === "zh" ? "只展示已识别到可直接执行命令的功能入口；每张卡片对应一个 demo、服务、评测或文档构建入口。" : "Only functional areas with direct runnable commands are shown; each card maps to a demo, service, evaluation, or docs build entry."}</p>
      <div class="feature-grid">
        ${runnableFeatures.map((feature, index) => `
          <article class="feature-card">
            <h3>${index + 1}. ${htmlText(feature.name)}</h3>
            <p>${htmlText(feature.purpose)}</p>
            <div class="inspector-section">
              <span class="label">${currentLang === "zh" ? "运行方式" : "Run command"}</span>
              ${renderCommandBlock(feature.commands)}
            </div>
            <div class="pill-row">${(feature.files || []).map((file) => fileButton(file, shortName(file, 36))).join("")}</div>
            ${renderInlineMedia(feature.media || [])}
          </article>
        `).join("")}
      </div>
    </section>
  `;
}

function renderCommandBlock(commands) {
  const clean = (commands || []).filter(isUsefulCommand);
  if (!clean.length) return "";
  return `<pre class="command-block"><code>${clean.map((command) => `$ ${escapeHtml(command)}`).join("\n")}</code></pre>`;
}

function renderInlineMedia(media) {
  if (!media.length) return "";
  return `
    <div class="inline-media">
      ${media.map((item) => {
        if (item.type === "video") {
          return `<figure class="media-card"><video controls src="${escapeHtml(item.url)}"></video><figcaption>${htmlText(item.label || item.feature || "")}</figcaption></figure>`;
        }
        if (item.type === "youtube") {
          return `<figure class="media-card youtube-card"><a href="${escapeHtml(item.url)}" target="_blank">${currentLang === "zh" ? "打开对应视频" : "Open related video"}</a><figcaption>${htmlText(item.label || item.feature || "")}</figcaption></figure>`;
        }
        return `<figure class="media-card"><img src="${escapeHtml(item.url)}" alt="${htmlText(item.label || "Repository media")}" loading="lazy" /><figcaption>${htmlText(item.label || item.feature || "")}</figcaption></figure>`;
      }).join("")}
    </div>
  `;
}

function metricCard(label, value) {
  return `<article class="metric-card"><span class="label">${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></article>`;
}

function fileButton(file, label = "") {
  if (!file) return "";
  return `<button type="button" class="file-chip" data-file="${escapeHtml(file)}">${escapeHtml(label || file)}</button>`;
}

async function openFilePreview(path) {
  if (!analysisId) return;
  ensureFileModal();
  const modal = $("fileModal");
  modal.classList.add("open");
  modal.innerHTML = `
    <div class="file-modal-panel">
      <div class="file-modal-head">
        <div>
          <span class="label">${currentLang === "zh" ? "源码预览" : "Source Preview"}</span>
          <h2>${escapeHtml(path)}</h2>
        </div>
        <button type="button" class="icon-close" aria-label="Close">×</button>
      </div>
      <div class="file-loading">${currentLang === "zh" ? "正在读取文件内容..." : "Loading file content..."}</div>
    </div>
  `;
  modal.querySelector(".icon-close").addEventListener("click", closeFilePreview);
  modal.addEventListener("click", (event) => {
    if (event.target === modal) closeFilePreview();
  }, { once: true });
  try {
    const file = await getJson(`/api/analysis/${analysisId}/file?path=${encodeURIComponent(path)}`);
    modal.innerHTML = renderFileModal(file);
    modal.querySelector(".icon-close").addEventListener("click", closeFilePreview);
  } catch (error) {
    modal.innerHTML = `
      <div class="file-modal-panel">
        <div class="file-modal-head">
          <div>
            <span class="label">${currentLang === "zh" ? "源码预览" : "Source Preview"}</span>
            <h2>${escapeHtml(path)}</h2>
          </div>
          <button type="button" class="icon-close" aria-label="Close">×</button>
        </div>
        <div class="file-error">${currentLang === "zh" ? "读取失败：该文件可能不在当前本地仓库快照中。" : "Failed to read this file from the local repository snapshot."}</div>
      </div>
    `;
    modal.querySelector(".icon-close").addEventListener("click", closeFilePreview);
  }
}

function ensureFileModal() {
  if ($("fileModal")) return;
  const modal = document.createElement("div");
  modal.id = "fileModal";
  modal.className = "file-modal";
  document.body.appendChild(modal);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeFilePreview();
  });
}

function closeFilePreview() {
  const modal = $("fileModal");
  if (modal) {
    modal.classList.remove("open");
    modal.innerHTML = "";
  }
}

function renderFileModal(file) {
  const lineCount = String(file.content || "").split("\n").length;
  return `
    <div class="file-modal-panel">
      <div class="file-modal-head">
        <div>
          <span class="label">${currentLang === "zh" ? "源码预览" : "Source Preview"}</span>
          <h2>${escapeHtml(file.path)}</h2>
        </div>
        <button type="button" class="icon-close" aria-label="Close">×</button>
      </div>
      <div class="file-meta-bar">
        <span>${currentLang === "zh" ? "语言" : "Language"}: ${escapeHtml(file.language || "text")}</span>
        <span>${currentLang === "zh" ? "大小" : "Size"}: ${formatBytes(file.size || 0)}</span>
        <span>${currentLang === "zh" ? "行数" : "Lines"}: ${lineCount}</span>
        ${file.truncated ? `<span class="warn">${currentLang === "zh" ? "已截断显示" : "truncated"}</span>` : ""}
      </div>
      <pre class="code-preview"><code>${escapeHtml(file.content || "")}</code></pre>
    </div>
  `;
}

function formatBytes(size) {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / 1024 / 1024).toFixed(2)} MB`;
}

function renderArchitecture() {
  const graph = analysis.architecture_graph;
  selectedNode = graph.nodes[0] || null;
  const target = $("architecturePage");
  target.className = "";
  target.innerHTML = `
    <div class="architecture-layout">
      <section class="graph-stage">
        <div class="graph-toolbar">
          <div>
            <strong>${t("architectureMap")}</strong>
            <p class="muted">${htmlText(graph.notice)}</p>
          </div>
          <div class="pill-row">
            <span class="pill">${htmlText("entry")}</span>
            <span class="pill">${htmlText("module")}</span>
            <span class="pill">${htmlText("utility")}</span>
          </div>
        </div>
        ${renderLogicalArchitecture(graph.logical_graph || {})}
        ${renderCallHierarchy(graph.call_hierarchy || {})}
        ${(graph.layers || []).length ? renderArchitectureLayers(graph.layers, graph.flow_story || graph.insight || "") : ""}
        ${renderArchitectureDetails(graph)}
        <div class="file-evidence-heading">
          <div>
            <span class="label">${t("evidenceGraph")}</span>
            <h2>${currentLang === "zh" ? "支撑上述逻辑图的文件级关系" : "File-level relations behind the logical map"}</h2>
          </div>
        </div>
        <div id="graphCanvas" class="graph-canvas"></div>
        <div class="mermaid-box">
          <h2>${t("coreFlow")}</h2>
          ${graph.flow_story ? `<p class="flow-story">${htmlText(graph.flow_story)}</p>` : ""}
          ${renderCoreFlow(graph.core_flow || [])}
        </div>
      </section>
      <aside id="nodeInspector" class="inspector"></aside>
    </div>
  `;
  drawGraph(graph);
  target.querySelectorAll(".file-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const path = chip.dataset.file;
      const node = (graph.nodes || []).find((item) => item.path === path);
      if (node) {
        selectedNode = node;
        renderInspector(selectedNode);
      }
    });
  });
  renderInspector(selectedNode);
}

function renderCallHierarchy(callGraph) {
  const modules = callGraph.modules || [];
  const functionEdges = callGraph.function_edges || [];
  const relationDetails = callGraph.relation_details || [];
  if (!modules.length) return "";
  return `
    <section class="call-hierarchy">
      <div class="section-heading">
        <div>
          <span class="label">${t("threeLevelCalls")}</span>
          <h2>${currentLang === "zh" ? "模块 -> 文件 -> 函数/类调用关系" : "Module -> File -> Function/Class Calls"}</h2>
          <p class="muted">${htmlText(callGraph.notice || (currentLang === "zh" ? "基于 Tree-sitter symbols、imports/includes 和 call expressions 的静态近似调用视图。" : "Static approximate call view from Tree-sitter symbols, imports/includes, and call expressions."))}</p>
        </div>
      </div>
      ${renderDetailedModuleRelations(relationDetails)}
      <div class="call-hierarchy-grid">
        ${modules.slice(0, 18).map((module) => `
          <article class="call-module-card">
            <div class="call-module-head">
              <span class="module-kind ${escapeHtml(module.kind || "core")}">${htmlText(module.name || module.id)}</span>
              <small>${currentLang === "zh" ? "模块" : "module"}</small>
            </div>
            <p>${htmlText(module.description || "")}</p>
            <div class="call-file-stack">
              ${(module.files || []).slice(0, 4).map((file) => renderCallFile(file)).join("")}
            </div>
          </article>
        `).join("")}
      </div>
      <div class="function-edge-panel">
        <div class="section-heading compact">
          <div>
            <span class="label">${currentLang === "zh" ? "函数调用样例" : "Function Call Samples"}</span>
            <h3>${currentLang === "zh" ? "从函数/类符号到调用表达式" : "From symbols to call expressions"}</h3>
          </div>
        </div>
        <div class="function-edge-list">
          ${functionEdges.slice(0, 48).map((edge) => `
            <article class="function-edge">
              <span>${escapeHtml(shortName(edge.source_file || "", 30))}</span>
              <strong>${escapeHtml(shortName(edge.source_function || "", 22))}</strong>
              <em>${htmlText(edge.relation || "calls")}</em>
              <strong>${escapeHtml(shortName(edge.target_function || "", 28))}</strong>
              <span>${edge.target_file ? escapeHtml(shortName(edge.target_file, 30)) : htmlText(edge.confidence || "name-only")}</span>
            </article>
          `).join("") || `<p class="muted">${currentLang === "zh" ? "当前没有提取到函数调用表达式。" : "No function call expressions were extracted."}</p>`}
        </div>
      </div>
    </section>
  `;
}

function renderDetailedModuleRelations(details) {
  if (!details.length) return "";
  return `
    <div class="detailed-relations">
      <div class="section-heading compact">
        <div>
          <span class="label">${currentLang === "zh" ? "详细模块调用说明" : "Detailed Module Call Explanation"}</span>
          <h3>${currentLang === "zh" ? "每条边都展开到文件、函数和阅读顺序" : "Each edge expanded into files, functions, and reading order"}</h3>
        </div>
      </div>
      <div class="relation-detail-grid">
        ${details.slice(0, 24).map((item, index) => `
          <article class="relation-detail-card">
            <div class="relation-detail-head">
              <span class="relation-number">${index + 1}</span>
              <div>
                <h4>${htmlText(item.source_name || item.source)} <em>${htmlText(item.relation || "calls")}</em> ${htmlText(item.target_name || item.target)}</h4>
                <p>${htmlText(item.purpose || "")}</p>
              </div>
              <strong>${currentLang === "zh" ? "权重" : "weight"} ${item.weight || 1}</strong>
            </div>
            <div class="relation-detail-body">
              <div>
                <span class="label">${currentLang === "zh" ? "源模块关键文件" : "Source files"}</span>
                <div class="pill-row">${(item.source_files || []).slice(0, 5).map((file) => fileButton(file, shortName(file, 38))).join("")}</div>
              </div>
              <div>
                <span class="label">${currentLang === "zh" ? "目标模块关键文件" : "Target files"}</span>
                <div class="pill-row">${(item.target_files || []).slice(0, 5).map((file) => fileButton(file, shortName(file, 38))).join("")}</div>
              </div>
              <div>
                <span class="label">${currentLang === "zh" ? "文件级调用 / include 证据" : "File-level import/include evidence"}</span>
                <div class="edge-evidence-list">
                  ${(item.file_edges || []).slice(0, 5).map((edge) => `
                    <div class="mini-edge">
                      ${fileButton(edge.source, shortName(edge.source, 32))}
                      <span>${htmlText(edge.relation || "imports")}</span>
                      ${fileButton(edge.target, shortName(edge.target, 32))}
                    </div>
                  `).join("") || (item.evidence || []).slice(0, 4).map((edge) => `<span class="pill">${escapeHtml(shortName(edge, 70))}</span>`).join("")}
                </div>
              </div>
              <div>
                <span class="label">${currentLang === "zh" ? "函数/类调用样例" : "Function/class call samples"}</span>
                <div class="function-mini-list">
                  ${(item.function_edges || []).slice(0, 6).map((edge) => `
                    <span>${escapeHtml(shortName(edge.source_function || "", 24))} -> ${escapeHtml(shortName(edge.target_function || "", 28))}</span>
                  `).join("") || `<span class="muted">${currentLang === "zh" ? "未解析到可跨文件定位的函数调用，展示文件级关系。" : "No cross-file function call was resolved; file-level relation is shown."}</span>`}
                </div>
              </div>
              <div class="reading-order">
                <span class="label">${currentLang === "zh" ? "建议阅读顺序" : "Suggested reading order"}</span>
                <ol>${(item.reading_order || []).slice(0, 6).map((file) => `<li>${fileButton(file, file)}</li>`).join("")}</ol>
              </div>
            </div>
            <p class="newcomer-note">${htmlText(item.newcomer_note || "")}</p>
          </article>
        `).join("")}
      </div>
    </div>
  `;
}

function renderCallFile(file) {
  const symbols = file.symbols || [];
  const calls = file.calls || [];
  return `
    <div class="call-file-card">
      ${fileButton(file.path, shortName(file.path, 48))}
      <div class="call-file-meta">
        <span>${currentLang === "zh" ? "分数" : "score"} ${file.importance_score || 0}</span>
        <span>${currentLang === "zh" ? "入" : "in"} ${(file.incoming_files || []).length}</span>
        <span>${currentLang === "zh" ? "出" : "out"} ${(file.outgoing_files || []).length}</span>
      </div>
      <div class="call-columns">
        <div>
          <span class="label">${currentLang === "zh" ? "函数/类" : "Symbols"}</span>
          <div class="pill-row">${symbols.slice(0, 5).map((item) => `<span class="pill">${escapeHtml(shortName(item, 24))}</span>`).join("") || `<span class="muted">${t("noSymbols")}</span>`}</div>
        </div>
        <div>
          <span class="label">${currentLang === "zh" ? "调用表达式" : "Call expressions"}</span>
          <div class="pill-row">${calls.slice(0, 6).map((call) => `<span class="pill ${call.resolved ? "resolved-call" : ""}">${escapeHtml(shortName(call.name, 26))}</span>`).join("") || `<span class="muted">${t("noImports")}</span>`}</div>
        </div>
      </div>
    </div>
  `;
}

function renderLogicalArchitecture(logical) {
  const nodes = logical.nodes || [];
  const edges = logical.edges || [];
  const chain = logical.core_chain || [];
  if (!nodes.length) return "";
  const nodeById = Object.fromEntries(nodes.map((node) => [node.id, node]));
  return `
    <section class="logical-architecture">
      <div class="section-heading">
        <div>
          <span class="label">${t("logicalArchitecture")}</span>
          <h2>${t("moduleCallGraph")}</h2>
          <p class="muted">${htmlText(logical.subtitle || (currentLang === "zh" ? "基于 Tree-sitter 符号、import、文件职责和 CodeGraph 边聚合得到。" : "Aggregated from Tree-sitter symbols, imports, file roles, and CodeGraph edges."))}</p>
        </div>
      </div>
      <div class="logical-grid">
        <div class="logical-map">
          ${renderLogicalSvg(nodes, edges)}
        </div>
        <div class="logical-side">
          <h3>${t("coreCallChain")}</h3>
          <div class="call-chain">
            ${chain.map((step) => `
              <article class="chain-step">
                <span>${step.step}</span>
                <div>
                  <strong>${htmlText(step.module)}</strong>
                  <p>${htmlText(step.summary || "")}</p>
                  <div class="pill-row">${(step.files || []).slice(0, 3).map((file) => fileButton(file, shortName(file, 28))).join("")}</div>
                </div>
              </article>
            `).join("")}
          </div>
        </div>
      </div>
      <div class="module-call-list">
        ${edges.slice(0, 30).map((edge) => {
          const source = nodeById[edge.source] || {};
          const target = nodeById[edge.target] || {};
          return `
            <article class="module-call-card">
              <div class="module-call-head">
                <strong>${htmlText(source.name || edge.source)}</strong>
                <span>${htmlText(edge.relation || "calls")}</span>
                <strong>${htmlText(target.name || edge.target)}</strong>
              </div>
              <p>${htmlText(renderEdgeExplanation(edge, source, target))}</p>
              <div class="pill-row">${(edge.evidence || []).slice(0, 3).map((item) => `<span class="pill">${escapeHtml(shortName(item, 56))}</span>`).join("")}</div>
            </article>
          `;
        }).join("")}
      </div>
    </section>
  `;
}

function renderEdgeExplanation(edge, source, target) {
  if (currentLang === "zh") {
    const relation = localize(edge.relation || "calls");
    return `${source.name || edge.source} ${relation} ${target.name || edge.target}；依据来自静态 import、符号和 CodeGraph 关系，权重 ${edge.weight || 1}。`;
  }
  return `${source.name || edge.source} ${edge.relation || "calls"} ${target.name || edge.target}; evidence comes from static imports, symbols, and CodeGraph relations. Weight ${edge.weight || 1}.`;
}

function renderLogicalSvg(nodes, edges) {
  const width = 1180;
  const height = Math.max(620, Math.ceil(nodes.length / 4) * 108 + 120);
  const positions = logicalPositions(nodes, width, height);
  const byId = Object.fromEntries(positions.map((node) => [node.id, node]));
  const edgeMarkup = edges.map((edge, index) => {
    const source = byId[edge.source];
    const target = byId[edge.target];
    if (!source || !target) return "";
    const sx = source.x + source.w / 2;
    const sy = source.y + source.h / 2;
    const tx = target.x + target.w / 2;
    const ty = target.y + target.h / 2;
    const midX = (sx + tx) / 2;
    const curve = Math.max(-70, Math.min(70, (target.y - source.y) * 0.16));
    return `
      <path class="logical-edge" d="M ${sx} ${sy} C ${midX} ${sy + curve}, ${midX} ${ty - curve}, ${tx} ${ty}" marker-end="url(#logicalArrow)" />
      <text class="logical-edge-label" x="${(sx + tx) / 2}" y="${(sy + ty) / 2 - 6}">${escapeSvg(shortName(localize(edge.relation || "calls"), 14))}</text>
    `;
  }).join("");
  const nodeMarkup = positions.map((node) => {
    const color = logicalColor(node.kind);
    return `
      <g class="logical-node logical-${escapeSvg(node.kind || "core")}" transform="translate(${node.x}, ${node.y})">
        <rect width="${node.w}" height="${node.h}" rx="14" fill="#fff" stroke="${color}" />
        <rect width="8" height="${node.h}" rx="4" fill="${color}" />
        <text x="20" y="26" class="logical-title">${escapeSvg(shortName(node.name, 26))}</text>
        <text x="20" y="48" class="logical-meta">${escapeSvg(localize(node.kind || "module"))} · ${node.file_count || 0} files · ${node.importance || 0}</text>
        <text x="20" y="70" class="logical-files">${escapeSvg(shortName((node.files || [])[0] || "", 32))}</text>
      </g>
    `;
  }).join("");
  return `
    <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Logical architecture module call graph">
      <defs>
        <marker id="logicalArrow" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto">
          <path d="M0,0 L0,9 L9,4.5 z" fill="#667085"></path>
        </marker>
      </defs>
      ${edgeMarkup}
      ${nodeMarkup}
    </svg>
  `;
}

function logicalPositions(nodes, width, height) {
  const columns = [
    { kinds: ["docs", "entry"], x: 24, title: currentLang === "zh" ? "入口/文档" : "Docs/Entry" },
    { kinds: ["app", "runtime"], x: 258, title: currentLang === "zh" ? "应用/运行时" : "App/Runtime" },
    { kinds: ["core"], x: 492, title: currentLang === "zh" ? "核心子系统" : "Core Subsystems" },
    { kinds: ["platform", "library", "config", "test"], x: 826, title: currentLang === "zh" ? "支撑/平台/验证" : "Support/Platform/Test" },
  ];
  const columnForKind = (kind) => columns.find((column) => column.kinds.includes(kind)) || columns[2];
  const grouped = new Map(columns.map((column) => [column.x, []]));
  nodes.forEach((node) => grouped.get(columnForKind(node.kind).x).push(node));
  const positioned = [];
  columns.forEach((column) => {
    const group = grouped.get(column.x) || [];
    group.forEach((node, index) => {
      const isCore = node.kind === "core";
      positioned.push({
        ...node,
        x: column.x + (isCore && index % 2 ? 164 : 0),
        y: 72 + Math.floor(index / (isCore ? 2 : 1)) * 102,
        w: isCore ? 154 : 208,
        h: 82,
        columnTitle: column.title,
      });
    });
  });
  return positioned;
}

function logicalColor(kind) {
  return {
    entry: "#2764c5",
    app: "#8b5cf6",
    core: "#16845b",
    runtime: "#0f766e",
    platform: "#b45309",
    library: "#6750a4",
    config: "#475467",
    test: "#c2410c",
    docs: "#2563eb",
  }[kind] || "#16845b";
}

function renderArchitectureDetails(graph) {
  const modules = graph.detailed_modules || [];
  const notes = graph.module_notes || [];
  const noteByFile = Object.fromEntries(notes.map((note) => [note.file, note]));
  const relations = graph.relationships || [];
  if (!modules.length && !relations.length) return "";
  return `
    <section class="architecture-details">
      <div class="section-heading">
        <div>
          <span class="label">${currentLang === "zh" ? "代码模块与调用关系" : "Code Modules & Relations"}</span>
          <h2>${currentLang === "zh" ? "从 AST/Import/DeepSeek 推理得到的模块关系" : "Module Relations from AST, Imports, and DeepSeek"}</h2>
        </div>
      </div>
      <div class="detail-grid">
        <div class="module-table">
          ${modules.slice(0, 10).map((module) => {
            const note = noteByFile[module.path] || {};
            const symbols = (note.key_symbols && note.key_symbols.length ? note.key_symbols : (module.symbols || []).map(symbolName)).slice(0, 6);
            const calls = (note.key_calls && note.key_calls.length ? note.key_calls : (module.calls || [])).slice(0, 8);
            return `
              <article class="module-row">
                <div>
                  <button class="module-path file-chip" data-file="${escapeHtml(module.path)}">${escapeHtml(module.path)}</button>
                  <p>${htmlText(note.responsibility || module.summary || "")}</p>
                  <div class="mini-columns">
                    <div>
                      <span class="label">${currentLang === "zh" ? "关键函数/类" : "Key Symbols"}</span>
                      <div class="pill-row">${symbols.map((item) => `<span class="pill">${escapeHtml(item)}</span>`).join("") || `<span class="muted">${t("noSymbols")}</span>`}</div>
                    </div>
                    <div>
                      <span class="label">${currentLang === "zh" ? "调用/依赖" : "Calls / Imports"}</span>
                      <div class="pill-row">${calls.map((item) => `<span class="pill">${escapeHtml(shortName(item, 28))}</span>`).join("") || (module.imports || []).slice(0, 6).map((item) => `<span class="pill">${escapeHtml(shortName(item, 28))}</span>`).join("") || `<span class="muted">${t("noImports")}</span>`}</div>
                    </div>
                  </div>
                </div>
                <div class="relation-counts">
                  <span>${currentLang === "zh" ? "入边" : "In"} ${(module.incoming || []).length}</span>
                  <span>${currentLang === "zh" ? "出边" : "Out"} ${(module.outgoing || []).length}</span>
                </div>
              </article>
            `;
          }).join("")}
        </div>
        <div class="relation-list">
          <h3>${currentLang === "zh" ? "关键关系链" : "Key Relation Chains"}</h3>
          ${relations.slice(0, 12).map((rel) => `
            <article class="relation-card">
              <div class="relation-line">
                <span>${escapeHtml(shortName(rel.source, 30))}</span>
                <strong>${htmlText(rel.type || "uses")}</strong>
                <span>${escapeHtml(shortName(rel.target, 30))}</span>
              </div>
              <p>${htmlText(rel.explanation || "")}</p>
            </article>
          `).join("") || `<p class="muted">${currentLang === "zh" ? "当前静态关系较稀疏，建议结合 Core Flow 阅读。" : "Static relations are sparse; combine this with Core Flow."}</p>`}
        </div>
      </div>
    </section>
  `;
}

function renderArchitectureLayers(layers, story) {
  return `
    <section class="ai-architecture">
      <div class="section-heading">
        <div>
          <span class="label">${currentLang === "zh" ? "DeepSeek 架构理解" : "DeepSeek Architecture Reasoning"}</span>
          <h2>${currentLang === "zh" ? "按系统职责重组的架构层" : "System Layers Reconstructed by Responsibility"}</h2>
        </div>
      </div>
      ${story ? `<p class="flow-story">${htmlText(story)}</p>` : ""}
      <div class="layer-map">
        ${layers.map((layer, index) => `
          <article class="layer-card layer-${escapeHtml(layer.type || "domain")}" data-layer-index="${index}">
            <div class="layer-head">
              <span class="layer-index">${index + 1}</span>
              <div>
                <h3>${htmlText(layer.name)}</h3>
                <span class="pill">${htmlText(layer.type || "domain")}</span>
              </div>
            </div>
            <p>${htmlText(layer.description || "")}</p>
            <div class="layer-files">
              ${(layer.files || []).slice(0, 5).map((file) => fileButton(file, shortName(file, 34))).join("")}
            </div>
            <div class="layer-why">${htmlText(layer.why_newcomers_read_it || "")}</div>
          </article>
        `).join("")}
      </div>
    </section>
  `;
}

function renderCoreFlow(flow) {
  if (!flow.length) {
    return `<p class="muted">${currentLang === "zh" ? "当前仓库的静态入口链路不足，建议从 README 和最高分核心模块开始。" : "Static entry flow is sparse; start from README and the highest-ranked core module."}</p>`;
  }
  return `
    <div class="core-flow-track">
      ${flow.map((item, index) => `
        <article class="flow-card">
          <div class="flow-step">${index + 1}</div>
          <div class="file-path">${escapeHtml(item.file)}</div>
          <div class="pill-row"><span class="pill">${htmlText(item.role)}</span></div>
          <p class="muted">${htmlText(item.summary || "")}</p>
        </article>
      `).join("")}
    </div>
  `;
}

function drawGraph(graph) {
  const canvas = $("graphCanvas");
  const nodes = graph.nodes || [];
  const edges = graph.edges || [];
  const width = Math.max(980, canvas.clientWidth || 980);
  const height = 520;
  const columns = {
    entry: nodes.filter((node) => node.category === "entry"),
    module: nodes.filter((node) => node.category === "module"),
    utility: nodes.filter((node) => node.category === "utility" || !["entry", "module"].includes(node.category)),
  };
  const positioned = [];
  [
    ["entry", 0.16],
    ["module", 0.5],
    ["utility", 0.84],
  ].forEach(([category, xRatio]) => {
    const group = columns[category] || [];
    const spacing = Math.min(96, Math.max(68, 390 / Math.max(1, group.length)));
    const startY = Math.max(60, 260 - ((group.length - 1) * spacing) / 2);
    group.forEach((node, index) => {
      positioned.push({
        ...node,
        x: width * xRatio - 82,
        y: startY + index * spacing,
      });
    });
  });
  if (!positioned.length) {
    nodes.forEach((node, index) => {
      const col = index % 4;
      const row = Math.floor(index / 4);
      positioned.push({
        ...node,
        x: 80 + col * ((width - 180) / 3),
        y: 64 + row * 105,
      });
    });
  }
  const byPath = Object.fromEntries(positioned.map((node) => [node.path, node]));
  const edgeMarkup = edges.map((edge) => {
    const source = byPath[edge.source];
    const target = byPath[edge.target];
    if (!source || !target) return "";
    return `<line x1="${source.x + 82}" y1="${source.y + 24}" x2="${target.x + 82}" y2="${target.y + 24}" stroke="#9aa9bb" stroke-width="1.4" marker-end="url(#arrow)" />`;
  }).join("");
  const nodeMarkup = positioned.map((node, index) => {
    const color = node.category === "entry" ? "#2764c5" : node.category === "module" ? "#16845b" : "#6750a4";
    return `
      <g class="graph-node" data-index="${index}" transform="translate(${node.x}, ${node.y})">
        <rect width="164" height="50" rx="10" fill="#ffffff" stroke="${color}" />
        <circle cx="17" cy="25" r="7" fill="${color}" />
        <text x="32" y="21" fill="#15202b">${escapeSvg(shortName(node.path, 18))}</text>
        <text x="32" y="38" fill="${color}">${escapeSvg(node.category)} · ${node.importance_score}</text>
      </g>
    `;
  }).join("");
  canvas.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="CodeGraph architecture">
      <defs>
        <marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
          <path d="M0,0 L0,6 L7,3 z" fill="#9aa9bb"></path>
        </marker>
      </defs>
      <text class="layer-label" x="${width * 0.16 - 82}" y="32">${escapeSvg(t("entryLayer"))}</text>
      <text class="layer-label" x="${width * 0.5 - 82}" y="32">${escapeSvg(t("coreLayer"))}</text>
      <text class="layer-label" x="${width * 0.84 - 82}" y="32">${escapeSvg(t("supportLayer"))}</text>
      ${edgeMarkup}
      ${nodeMarkup}
    </svg>
  `;
  canvas.querySelectorAll(".graph-node").forEach((nodeEl) => {
    nodeEl.addEventListener("click", () => {
      selectedNode = positioned[Number(nodeEl.dataset.index)];
      renderInspector(selectedNode);
    });
  });
}

function renderInspector(node) {
  const target = $("nodeInspector");
  if (!node) {
    target.innerHTML = `<h2>${t("inspector")}</h2><p class='muted'>${currentLang === "zh" ? "选择一个节点。" : "Select a node."}</p>`;
    return;
  }
  target.innerHTML = `
    <h2>${t("inspector")}</h2>
    ${fileButton(node.path, node.path)}
    <div class="pill-row">
      <span class="pill">${htmlText(node.category)}</span>
      <span class="pill">${htmlText(node.type)}</span>
      <span class="pill">score ${node.importance_score}</span>
    </div>
    <div class="inspector-section">
      <span class="label">${t("role")}</span>
      <p>${htmlText(node.summary || "")}</p>
    </div>
    <div class="inspector-section">
      <span class="label">${t("keySymbols")}</span>
      <div class="pill-row">${(node.symbols || []).slice(0, 8).map((s) => `<span class="pill">${escapeHtml(symbolLabel(s))}</span>`).join("") || `<span class='muted'>${t("noSymbols")}</span>`}</div>
    </div>
    <div class="inspector-section">
      <span class="label">${t("imports")}</span>
      <div class="pill-row">${(node.imports || []).slice(0, 8).map((item) => `<span class="pill">${escapeHtml(shortName(item, 26))}</span>`).join("") || `<span class='muted'>${t("noImports")}</span>`}</div>
    </div>
    <div class="inspector-section">
      <span class="label">${t("whyRead")}</span>
      <p>${htmlText(node.newcomer_reason || node.why_important || "")}</p>
    </div>
  `;
}

function mermaidFlow(flow) {
  if (!flow.length) return "flowchart LR\n  A[README] --> B[Entry File] --> C[Core Module]";
  const lines = ["flowchart LR"];
  flow.forEach((item, index) => {
    lines.push(`  N${index}["${item.step}. ${sanitizeMermaid(shortName(item.file, 28))}"]`);
    if (index > 0) lines.push(`  N${index - 1} --> N${index}`);
  });
  return lines.join("\n");
}

function symbolName(symbol) {
  if (!symbol) return "";
  if (typeof symbol === "string") return symbol.replace(/^@\{name=([^;]+).*$/, "$1");
  return symbol.name || "";
}

function symbolLabel(symbol) {
  if (!symbol) return "";
  if (typeof symbol === "string") return symbol.replace(/^@\{name=([^;]+); kind=([^;]+).*$/, "$2 $1");
  return `${symbol.kind || "symbol"} ${symbol.name || ""}`.trim();
}

function renderMermaid() {
  if (window.mermaid) {
    try {
      window.mermaid.initialize({ startOnLoad: false, theme: "base" });
      window.mermaid.run({ querySelector: ".mermaid" });
    } catch (_) {
      // The SVG graph above is the deterministic fallback.
    }
  }
}

function renderLearning() {
  const steps = analysis.learning_path || [];
  const quiz = analysis.checkpoint_quiz || [];
  const profile = analysis.repo_profile || {};
  const totalMinutes = steps.reduce((sum, step) => sum + parseMinutes(step.estimated_time), 0);
  const phaseNames = currentLang === "zh"
    ? ["建立心智模型", "复现与入口定位", "核心代码深读", "首次贡献准备"]
    : ["Mental Model", "Reproduce & Locate Entry", "Deep Read Core", "Prepare First PR"];
  const target = $("learningPage");
  target.className = "";
  target.innerHTML = `
    <div class="planner-shell">
      <section class="planner-hero panel">
        <div>
          <span class="label">${currentLang === "zh" ? "学习路径规划器" : "Learning Path Planner"}</span>
          <h2>${currentLang === "zh" ? "从看懂仓库到完成首次贡献的可执行路线" : "Executable route from repository understanding to first contribution"}</h2>
          <p>${htmlText(localizedField(profile, "one_liner") || (currentLang === "zh" ? "RepoPilot 已根据角色、目标、入口文件和 CodeGraph 生成学习计划。" : "RepoPilot generated this plan from role, goal, entry files, and CodeGraph."))}</p>
        </div>
        <div class="planner-stats">
          <div><span>${currentLang === "zh" ? "步骤" : "Steps"}</span><strong>${steps.length}</strong></div>
          <div><span>${currentLang === "zh" ? "预计" : "ETA"}</span><strong>${totalMinutes || "--"} min</strong></div>
          <div><span>${currentLang === "zh" ? "目标" : "Goal"}</span><strong>${htmlText(profile.goal || $("goal").selectedOptions[0]?.textContent || "-")}</strong></div>
        </div>
      </section>

      <section class="planner-map panel">
        <div class="section-heading">
          <div>
            <span class="label">${currentLang === "zh" ? "路径总览" : "Route Overview"}</span>
            <h2>${currentLang === "zh" ? "四阶段学习路线" : "Four-phase onboarding route"}</h2>
          </div>
        </div>
        <div class="phase-rail">
          ${phaseNames.map((name, index) => `
            <div class="phase-node">
              <span>${index + 1}</span>
              <strong>${name}</strong>
              <small>${currentLang === "zh" ? "由 Agent 规划" : "Agent planned"}</small>
            </div>
          `).join("")}
        </div>
      </section>

      <section class="planner-board">
        ${steps.map((step, index) => renderPlannerStep(step, index, steps.length)).join("")}
      </section>

      <section class="planner-bottom">
        <aside class="panel planner-checklist">
          <h2>${currentLang === "zh" ? "执行清单" : "Execution Checklist"}</h2>
          <ul class="check-list">
            ${steps.map((step) => `<li>${htmlText(step.title)}：${htmlText(step.checkpoint || "")}</li>`).join("")}
          </ul>
        </aside>
        <aside class="panel">
          <h2>${t("checkpointQuiz")}</h2>
          <ul class="quiz-list">
            ${quiz.map((item) => `
              <li>
                <strong>${htmlText(item.question)}</strong>
                <p class="muted">${t("expectedAnswer")}: ${htmlText(item.answer)}</p>
              </li>
            `).join("")}
          </ul>
        </aside>
      </section>
    </div>
  `;
}

function renderPlannerStep(step, index, total) {
  const files = step.files || [];
  const phase = Math.min(4, Math.max(1, Math.ceil(((index + 1) / Math.max(1, total)) * 4)));
  const deliverable = currentLang === "zh"
    ? ["一句话项目解释", "可复现运行记录", "核心调用链笔记", "首次 PR 变更计划"][phase - 1]
    : ["One-sentence project explanation", "Reproduction log", "Core call-chain notes", "First PR change plan"][phase - 1];
  return `
    <article class="planner-step-card">
      <div class="planner-step-head">
        <div class="step-index">${step.index || index + 1}</div>
        <div>
          <span class="label">${currentLang === "zh" ? `阶段 ${phase}` : `Phase ${phase}`}</span>
          <h3>${htmlText(step.title)}</h3>
        </div>
        <span class="time-badge">${htmlText(step.estimated_time || "")}</span>
      </div>
      <p class="planner-objective">${htmlText(step.objective)}</p>
      <div class="planner-step-grid">
        <div>
          <span class="label">${currentLang === "zh" ? "推荐文件" : "Files"}</span>
          <div class="pill-row">${files.map((file) => fileButton(file, shortName(file, 36))).join("") || `<span class="muted">README.md</span>`}</div>
        </div>
        <div>
          <span class="label">${t("readingReason")}</span>
          <p>${htmlText(step.reason || "")}</p>
        </div>
        <div>
          <span class="label">${currentLang === "zh" ? "本步产出" : "Deliverable"}</span>
          <p>${htmlText(deliverable)}</p>
        </div>
        <div>
          <span class="label">${t("checkpoint")}</span>
          <p>${htmlText(step.checkpoint || "")}</p>
        </div>
      </div>
    </article>
  `;
}

function parseMinutes(value) {
  const match = String(value || "").match(/(\d+)/);
  return match ? Number(match[1]) : 0;
}

function renderContribution() {
  const tasks = analysis.contribution_tasks || [];
  const strategy = analysis.contribution_strategy || {};
  const radarPoints = layoutRadarDots(tasks);
  const target = $("contributionPage");
  target.className = "";
  target.innerHTML = `
    ${strategy.summary || strategy.best_first_task ? `
      <section class="contribution-strategy">
        <div>
          <span class="label">${currentLang === "zh" ? "DeepSeek 贡献顾问" : "DeepSeek Contribution Advisor"}</span>
          <h2>${htmlText(strategy.best_first_task || (currentLang === "zh" ? "首次贡献策略" : "First Contribution Strategy"))}</h2>
          <p>${htmlText(strategy.summary || "")}</p>
          ${strategy.selection_reason ? `<p class="muted">${htmlText(strategy.selection_reason)}</p>` : ""}
        </div>
        ${(strategy.avoid_for_first_pr || []).length ? `
          <aside>
            <span class="label">${currentLang === "zh" ? "首次 PR 暂避区域" : "Avoid in First PR"}</span>
            <div class="pill-row">${strategy.avoid_for_first_pr.map((item) => `<span class="pill warning-pill">${htmlText(item)}</span>`).join("")}</div>
          </aside>
        ` : ""}
      </section>
    ` : ""}
    <div class="radar-layout">
      <section class="matrix">
        <div class="matrix-note">
          <strong>${currentLang === "zh" ? "贡献机会矩阵" : "Contribution Opportunity Matrix"}</strong>
          <p>${currentLang === "zh" ? "每个编号点对应右侧一个 DeepSeek 推荐任务。越靠左越适合新手，越靠上影响力越高。" : "Each numbered point maps to a DeepSeek-recommended task on the right. Left means easier for newcomers; higher means larger project impact."}</p>
        </div>
        <div class="quadrant q1">${currentLang === "zh" ? "首选区域" : "Best first PR"}</div>
        <div class="quadrant q2">${currentLang === "zh" ? "高影响但更难" : "High impact, harder"}</div>
        <div class="quadrant q3">${currentLang === "zh" ? "低风险练手" : "Low-risk practice"}</div>
        <div class="quadrant q4">${currentLang === "zh" ? "暂不推荐" : "Defer for later"}</div>
        <span class="axis x">${t("matrixX")}</span>
        <span class="axis y">${t("matrixY")}</span>
        ${tasks.map((task, index) => `
          <div class="task-dot" title="${htmlText(task.title)}" style="left:${radarPoints[index].x}%; bottom:${radarPoints[index].y}%; background:${task.difficulty === "Beginner" ? "var(--green)" : task.difficulty === "Intermediate" ? "var(--amber)" : "var(--red)"}">${index + 1}</div>
        `).join("")}
      </section>
      <section>
        ${tasks.map((task, index) => `
          <article class="task-card">
            <div class="task-head">
              <div>
                <h3>${index + 1}. ${htmlText(task.title)}</h3>
                <p class="muted">${htmlText(task.source)}</p>
              </div>
              <span class="difficulty ${escapeHtml(task.difficulty)}">${htmlText(task.difficulty)}</span>
            </div>
            <p>${htmlText(task.reason || "")}</p>
            <div class="pill-row">${(task.files || []).map((file) => fileButton(file, shortName(file, 36))).join("")}</div>
            <div class="pill-row">${(task.knowledge || []).map((item) => `<span class="pill">${htmlText(item)}</span>`).join("")}</div>
            ${(task.evidence || []).length ? `
              <div class="inspector-section">
                <span class="label">${currentLang === "zh" ? "DeepSeek 依据" : "DeepSeek Evidence"}</span>
                <ul class="compact-list">${task.evidence.map((item) => `<li>${htmlText(item)}</li>`).join("")}</ul>
              </div>
            ` : ""}
            <div class="inspector-section">
              <span class="label">${t("firstPrPlan")}</span>
              <ol>${(task.first_pr_plan || []).map((step) => `<li>${htmlText(step)}</li>`).join("")}</ol>
            </div>
            ${(task.verification || []).length ? `
              <div class="inspector-section">
                <span class="label">${currentLang === "zh" ? "验证方式" : "Verification"}</span>
                <div class="command-mini">${task.verification.map((item) => `<code>${escapeHtml(item)}</code>`).join("")}</div>
              </div>
            ` : ""}
            ${task.pr_title || task.maintainer_pitch ? `
              <div class="pr-draft">
                ${task.pr_title ? `<strong>${htmlText(task.pr_title)}</strong>` : ""}
                ${task.maintainer_pitch ? `<p>${htmlText(task.maintainer_pitch)}</p>` : ""}
              </div>
            ` : ""}
            ${task.risk ? `<p class="risk-line">${htmlText(task.risk)}</p>` : ""}
          </article>
        `).join("")}
      </section>
    </div>
  `;
}

function layoutRadarDots(tasks) {
  const placed = [];
  const minGap = 8.5;
  return tasks.map((task, index) => {
    const baseX = Math.min(90, Math.max(10, Number(task.difficulty_score) || 45));
    const baseY = Math.min(88, Math.max(12, Number(task.impact_score) || 45));
    let point = { x: baseX, y: baseY };
    for (let attempt = 0; attempt < 18; attempt += 1) {
      const tooClose = placed.some((other) => Math.hypot(point.x - other.x, point.y - other.y) < minGap);
      if (!tooClose) break;
      const ring = 1 + Math.floor(attempt / 6);
      const angle = ((attempt * 137 + index * 43) % 360) * Math.PI / 180;
      point = {
        x: Math.min(92, Math.max(8, baseX + Math.cos(angle) * minGap * ring)),
        y: Math.min(90, Math.max(10, baseY + Math.sin(angle) * minGap * ring)),
      };
    }
    placed.push(point);
    return {
      x: point.x.toFixed(1),
      y: point.y.toFixed(1),
    };
  });
}
function renderTrace() {
  const agents = analysis.agent_trace || [];
  const reflection = analysis.reflection || {};
  const target = $("tracePage");
  target.className = "";
  target.innerHTML = `
    <section class="agent-grid">
      ${agents.map((agent, index) => `
        <article class="agent-card">
          <h3>${index + 1}. ${htmlText(agent.agent)}</h3>
          <div class="inspector-section"><span class="label">${t("input")}</span><p>${htmlText(agent.input)}</p></div>
          <div class="inspector-section"><span class="label">${t("action")}</span><p>${htmlText(agent.action)}</p></div>
          <div class="inspector-section"><span class="label">${t("output")}</span><p>${htmlText(agent.output)}</p></div>
          <div class="inspector-section"><span class="label">${t("nextStep")}</span><p>${htmlText(agent.next_step)}</p></div>
          <div class="confidence"><span style="width:${Math.round(agent.confidence * 100)}%"></span></div>
          <p class="muted">${t("confidence")} ${Math.round(agent.confidence * 100)}%</p>
        </article>
      `).join("")}
    </section>
    <section class="reflection">
      <h2>${t("reflectionAgent")}</h2>
      <div class="overview-layout">
        <div>
          <span class="label">${t("limitations")}</span>
          <ul>${(reflection.limitations || []).map((item) => `<li>${htmlText(item)}</li>`).join("")}</ul>
        </div>
        <div>
          <span class="label">${t("recommendedNextInput")}</span>
          <ul>${(reflection.recommended_next_input || []).map((item) => `<li>${htmlText(item)}</li>`).join("")}</ul>
        </div>
      </div>
    </section>
  `;
}

function renderChat() {
  const target = $("chatPage");
  if (!analysis) {
    target.className = "empty-state";
    target.innerHTML = t("emptyChat");
    return;
  }
  target.className = "";
  const suggestions = currentLang === "zh"
    ? ["我应该先读哪个文件？", "这个项目的核心调用链是什么？", "如何在本地跑起来？", "哪个任务最适合作为首次 PR？"]
    : ["Which file should I read first?", "What is the core call chain?", "How do I run it locally?", "Which task is best for my first PR?"];
  target.innerHTML = `
    <section class="chat-shell">
      <aside class="chat-context">
        <span class="label">RepoPilot Chat Agent</span>
        <h2>${t("chatTitle")}</h2>
        <p>${t("chatSubtitle")}</p>
        <div class="chat-context-grid">
          <div><span class="label">${t("modules")}</span><strong>${analysis.metrics?.modules || 0}</strong></div>
          <div><span class="label">${t("relations")}</span><strong>${analysis.metrics?.relations || 0}</strong></div>
          <div><span class="label">LLM</span><strong>${htmlText(analysis.repo_profile?.llm_status || "fallback")}</strong></div>
        </div>
        <div class="inspector-section">
          <span class="label">${t("suggestedQuestions")}</span>
          <div class="suggestion-list">
            ${suggestions.map((item) => `<button type="button" class="suggestion-chip" data-question="${escapeHtml(item)}">${escapeHtml(item)}</button>`).join("")}
          </div>
        </div>
      </aside>
      <section class="chat-panel">
        <div id="chatMessages" class="chat-messages">
          ${renderChatMessages()}
        </div>
        <form id="chatForm" class="chat-form">
          <input id="chatInput" type="text" placeholder="${t("chatPlaceholder")}" autocomplete="off" />
          <button type="submit">${t("send")}</button>
        </form>
      </section>
    </section>
  `;
  $("chatForm").addEventListener("submit", submitChat);
  target.querySelectorAll(".suggestion-chip").forEach((button) => {
    button.addEventListener("click", () => {
      $("chatInput").value = button.dataset.question || "";
      $("chatForm").dispatchEvent(new Event("submit", { cancelable: true }));
    });
  });
}

function renderChatMessages() {
  if (!chatHistory.length) {
    return `
      <article class="chat-message assistant">
        <strong>RepoPilot</strong>
        <p>${currentLang === "zh" ? "我已经读取当前 AnalysisResult。你可以问我：先看哪个文件、架构怎么走、如何运行、首次 PR 怎么选。" : "I have loaded the current AnalysisResult. Ask me about files, architecture, setup, or first PR strategy."}</p>
      </article>
    `;
  }
  return chatHistory.map((message) => `
    <article class="chat-message ${message.role}">
      <strong>${message.role === "user" ? (currentLang === "zh" ? "你" : "You") : "RepoPilot"}</strong>
      <p>${htmlText(message.content, { preserveMixedTechnicalText: true })}</p>
      ${message.citations?.length ? `<div class="pill-row">${message.citations.map((item) => `<span class="pill">${escapeHtml(item)}</span>`).join("")}</div>` : ""}
      ${message.next_actions?.length ? `<ul class="compact-list">${message.next_actions.map((item) => `<li>${htmlText(item, { preserveMixedTechnicalText: true })}</li>`).join("")}</ul>` : ""}
      ${message.llm_stage ? renderChatLlmStage(message.llm_stage, message.agent_trace || []) : ""}
      ${message.llm_status ? `<span class="chat-status">${escapeHtml(message.llm_status)}</span>` : ""}
    </article>
  `).join("");
}

function renderChatLlmStage(stage, trace) {
  const sections = stage.input_sections || [];
  return `
    <div class="chat-llm-stage">
      <div class="llm-stage-head">
        <span class="label">${currentLang === "zh" ? "LLM 环节" : "LLM Stage"}</span>
        <strong>${escapeHtml(stage.provider || "LLM")} · ${escapeHtml(stage.model || "")}</strong>
        <span>${currentLang === "zh" ? "状态" : "Status"}: ${escapeHtml(stage.status || "-")}</span>
      </div>
      ${sections.length ? `<div class="pill-row">${sections.map((item) => `<span class="pill">${htmlText(item)}</span>`).join("")}</div>` : ""}
      ${trace.length ? `
        <ol class="chat-trace">
          ${trace.map((item) => `
            <li>
              <strong>${escapeHtml(formatTraceStep(item.step))}</strong>
              <span>${htmlText(item.detail)}</span>
            </li>
          `).join("")}
        </ol>
      ` : ""}
    </div>
  `;
}

function formatTraceStep(step) {
  const map = currentLang === "zh"
    ? {
        understand_question: "理解问题",
        retrieve_context: "检索上下文",
        llm_reasoning: "DeepSeek LLM 推理",
        compose_answer: "生成回答",
      }
    : {
        understand_question: "Understand Question",
        retrieve_context: "Retrieve Context",
        llm_reasoning: "DeepSeek LLM Reasoning",
        compose_answer: "Compose Answer",
      };
  return map[step] || step;
}

async function submitChat(event) {
  event.preventDefault();
  const input = $("chatInput");
  const message = input.value.trim();
  if (!message || !analysisId) return;
  input.value = "";
  const previousHistory = chatHistory
    .filter((item) => item.role === "user" || item.role === "assistant")
    .filter((item) => typeof item.content === "string" && item.content.trim())
    .map((item) => ({ role: item.role, content: item.content }))
    .slice(-8);
  chatHistory.push({ role: "user", content: message });
  chatHistory.push({ role: "assistant", content: currentLang === "zh" ? "正在检索 AnalysisResult 并生成回答..." : "Retrieving AnalysisResult and composing an answer..." });
  refreshChatMessages();
  const payload = {
    analysis_id: analysisId,
    message,
    history: previousHistory,
    lang: currentLang,
  };
  try {
    const response = await postJson("/api/chat", payload);
    chatHistory.pop();
    chatHistory.push({
      role: "assistant",
      content: response.answer,
      citations: response.citations || [],
      next_actions: response.next_actions || [],
      llm_status: response.llm_status || "",
      llm_stage: response.llm_stage || null,
      agent_trace: response.agent_trace || [],
    });
  } catch (error) {
    chatHistory.pop();
    chatHistory.push({ role: "assistant", content: `${t("analysisFailed")}: ${error.message}` });
  }
  refreshChatMessages();
}

function refreshChatMessages() {
  const box = $("chatMessages");
  if (!box) return;
  box.innerHTML = renderChatMessages();
  box.scrollTop = box.scrollHeight;
}

async function getJson(url) {
  const finalUrl = withLang(url);
  const response = await fetch(finalUrl, { cache: "no-store" });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

function withLang(url) {
  if (!url.startsWith("/api/analysis") && !url.startsWith("/api/demo-analysis")) return url;
  const separator = url.includes("?") ? "&" : "?";
  return /[?&]lang=/.test(url) ? url : `${url}${separator}lang=${currentLang}`;
}

async function postJson(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

function shortName(value, limit = 22) {
  const text = String(value || "");
  if (text.length <= limit) return text;
  return `...${text.slice(-(limit - 3))}`;
}

function sanitizeMermaid(value) {
  return String(value).replaceAll('"', "'");
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function escapeSvg(value) {
  return escapeHtml(value);
}

