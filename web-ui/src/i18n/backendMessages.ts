// Maps the Chinese messages returned by the backend to i18n keys under `backend.*`.
// Unmatched text is shown as-is, so new backend messages never break the UI.
interface BackendMessageRule {
  key: string
  re: RegExp
}

const exact = (text: string) => new RegExp(`^${text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}$`)

export const BACKEND_MESSAGE_RULES: BackendMessageRule[] = [
  // results
  { key: 'invalidFilePath', re: exact('非法的文件路径') },
  { key: 'onlyJsonl', re: exact('只能删除 .jsonl 文件') },
  { key: 'fileNotFound', re: exact('文件不存在') },
  { key: 'fileDeleted', re: /^文件 (?<name>.+) 已成功删除$/ },
  { key: 'filtersConflict', re: exact('AI推荐筛选与关键词推荐筛选不能同时开启。') },
  { key: 'readResultError', re: /^读取结果文件时出错: (?<error>[\s\S]+)$/ },
  { key: 'exportResultError', re: /^导出结果文件时出错: (?<error>[\s\S]+)$/ },
  { key: 'resultNotFound', re: exact('结果文件未找到') },
  { key: 'itemNotFound', re: exact('商品未找到') },
  { key: 'statusUpdated', re: exact('状态已更新') },
  { key: 'blacklistUpdated', re: exact('黑名单规则已更新') },
  // tasks
  { key: 'fixedAccountRequired', re: exact('固定账号模式下必须选择账号。') },
  { key: 'taskNotFound', re: exact('任务未找到') },
  { key: 'taskCreated', re: /^任务创建成功。?$/ },
  { key: 'generationStarted', re: exact('AI 任务生成已开始。') },
  { key: 'jobNotFound', re: exact('任务生成作业未找到') },
  { key: 'keywordRequired', re: exact('关键词模式下至少需要一个关键词。') },
  { key: 'aiDescriptionRequired', re: exact('AI 模式下详细需求不能为空。') },
  { key: 'aiEmptyCriteria', re: exact('AI 未能生成分析标准，返回内容为空。') },
  { key: 'taskUpdated', re: exact('任务更新成功') },
  { key: 'taskDeleted', re: exact('任务删除成功') },
  { key: 'taskDisabled', re: exact('任务已被禁用，无法启动') },
  { key: 'taskAlreadyRunning', re: exact('任务已在运行中') },
  { key: 'taskStartFailed', re: exact('启动任务失败') },
  { key: 'taskStarted', re: /^任务 '(?<name>.+)' 已启动$/ },
  { key: 'taskStopSent', re: /^任务ID (?<id>.+) 已发送停止信号$/ },
  // task generation
  { key: 'genReceived', re: exact('已接收请求，开始准备分析标准。') },
  { key: 'genReadingReference', re: exact('正在读取参考文件。') },
  { key: 'genBuildingPrompt', re: exact('正在构建发送给 AI 的指令。') },
  { key: 'genCallingAi', re: exact('正在调用 AI 生成分析标准。') },
  { key: 'genSaving', re: /^正在保存分析标准到 (?<file>.+)。$/ },
  { key: 'genCreatingTask', re: exact('分析标准已生成，正在创建任务记录。') },
  { key: 'genDone', re: /^任务“(?<name>.+)”创建完成。$/ },
  { key: 'genFailed', re: /^AI 任务生成失败: (?<error>[\s\S]+)$/ },
  { key: 'stepPrepare', re: exact('接收创建请求') },
  { key: 'stepReference', re: exact('读取参考文件') },
  { key: 'stepPrompt', re: exact('构建提示词') },
  { key: 'stepLlm', re: exact('调用 AI 生成标准') },
  { key: 'stepPersist', re: exact('保存分析标准') },
  { key: 'stepTask', re: exact('创建任务记录') },
  // accounts
  { key: 'accountNameInvalid', re: exact('账号名称只能包含字母、数字、下划线或短横线。') },
  { key: 'invalidJson', re: exact('提供的内容不是有效的JSON格式。') },
  { key: 'accountNotFound', re: exact('账号不存在') },
  { key: 'accountExists', re: exact('账号已存在') },
  { key: 'accountAdded', re: exact('账号已添加') },
  { key: 'accountUpdated', re: exact('账号已更新') },
  { key: 'accountDeleted', re: exact('账号已删除') },
  // login state
  { key: 'loginStateUpdated', re: /^登录状态文件 '(?<name>.+)' 已成功更新。$/ },
  { key: 'loginStateWriteError', re: /^写入登录状态文件时出错: (?<error>[\s\S]+)$/ },
  { key: 'loginStateDeleted', re: exact('登录状态文件已成功删除。') },
  { key: 'loginStateDeleteError', re: /^删除登录状态文件时出错: (?<error>[\s\S]+)$/ },
  { key: 'loginStateMissing', re: exact('登录状态文件不存在，无需删除。') },
  // prompts
  { key: 'invalidFilename', re: exact('无效的文件名') },
  { key: 'promptNotFound', re: exact('Prompt 文件未找到') },
  { key: 'promptUpdated', re: /^Prompt 文件 '(?<name>.+)' 更新成功$/ },
  { key: 'writeFileError', re: /^写入文件时出错: (?<error>[\s\S]+)$/ },
  // dashboard
  { key: 'dashboardLoadFailed', re: /^加载 dashboard 数据失败: (?<error>[\s\S]+)$/ },
  // settings
  { key: 'notificationUpdateFailed', re: exact('更新通知设置失败') },
  { key: 'notificationUpdated', re: exact('通知设置已成功更新') },
  { key: 'channelUnsupported', re: /^渠道 (?<channel>.+) 未配置或不受支持$/ },
  { key: 'channelRequired', re: exact('请至少配置一个可用的通知渠道') },
  { key: 'notificationTested', re: exact('测试通知已执行') },
  { key: 'sendSuccess', re: exact('发送成功') },
  { key: 'rotationUpdateFailed', re: exact('更新轮换设置失败') },
  { key: 'rotationUpdated', re: exact('轮换设置已成功更新') },
  { key: 'aiUpdateFailed', re: exact('更新AI设置失败') },
  { key: 'aiUpdated', re: exact('AI设置已成功更新') },
  // logs
  { key: 'logNoTask', re: exact('未指定任务，无法清空日志。') },
  { key: 'logTaskMissing', re: exact('任务不存在或已删除。') },
  { key: 'logFileMissing', re: exact('日志文件不存在，无需清空。') },
  { key: 'logCleared', re: exact('日志已成功清空。') },
  { key: 'logClearError', re: /^清空日志文件时出错: (?<error>[\s\S]+)$/ },
]
