NORMAL_PERMISSION = "normal"
BENCHMARK_ACCESS_PERMISSION = "benchmark_access"
SIMULATION_LOG_PERMISSION = "simulation_log"
PERFORMANCE_ACCESS_PERMISSION = "performance_access"
TEAM_ACCESS_PERMISSION = "team_access"
DEMAND_ACCESS_PERMISSION = "demand_access"

BENCHMARK_VIEW_RESOURCE = "benchmark.view"
SIMULATION_TASK_RESOURCE = "simulation.task"
SIMULATION_LOG_RESOURCE = "simulation.log"
PERFORMANCE_VIEW_RESOURCE = "performance.view"
TEAM_VIEW_RESOURCE = "team.view"
DEMAND_VIEW_RESOURCE = "demand.view"
USAGE_ANALYTICS_RESOURCE = "analytics.usage"
PERMISSION_MANAGE_RESOURCE = "permission.manage"
ADMIN_MANAGE_RESOURCE = "admin.manage"
CORE_ADMIN_RESOURCES = {
    PERMISSION_MANAGE_RESOURCE,
    ADMIN_MANAGE_RESOURCE,
    USAGE_ANALYTICS_RESOURCE,
}

SESSION_COOKIE_NAME = "platform_session"

# Code registers stable identifiers and safe defaults. Names and policies are copied
# into the database on first registration and are subsequently editable by admins.
PERMISSION_SET_REGISTRY = {
    NORMAL_PERMISSION: {
        "name": "平台基础权限",
        "description": "登录平台后默认具备的基础访问权限。",
        "requestable": False,
        "system_managed": True,
    },
    BENCHMARK_ACCESS_PERMISSION: {
        "name": "Benchmark 访问权限",
        "description": "浏览芯片、Benchmark 定义和测试结果。",
        "requestable": True,
        "system_managed": False,
    },
    SIMULATION_LOG_PERMISSION: {
        "name": "Simulator 日志访问权限",
        "description": "查看本人仿真任务的运行日志。",
        "requestable": True,
        "system_managed": False,
    },
    PERFORMANCE_ACCESS_PERMISSION: {
        "name": "性能分析访问权限",
        "description": "使用 Trace 分析工作台进行日志分析与瓶颈定位。",
        "requestable": False,
        "system_managed": False,
    },
    TEAM_ACCESS_PERMISSION: {
        "name": "团队风采访问权限",
        "description": "查看团队成员、重点成果与贡献信息。",
        "requestable": False,
        "system_managed": False,
    },
    DEMAND_ACCESS_PERMISSION: {
        "name": "需求池访问权限",
        "description": "浏览、提交并支持平台共建需求。",
        "requestable": False,
        "system_managed": False,
    },
}

RESOURCE_REGISTRY = {
    SIMULATION_TASK_RESOURCE: {
        "name": "Simulator 任务",
        "description": "创建和查看本人仿真任务。",
        "access_mode": "normal",
        "permissions": [],
    },
    SIMULATION_LOG_RESOURCE: {
        "name": "Simulator 日志",
        "description": "查看本人仿真任务日志。",
        "access_mode": "permission",
        "permissions": [SIMULATION_LOG_PERMISSION],
    },
    BENCHMARK_VIEW_RESOURCE: {
        "name": "Benchmark",
        "description": "浏览芯片与 Benchmark 资产。",
        "access_mode": "permission",
        "permissions": [BENCHMARK_ACCESS_PERMISSION],
    },
    PERFORMANCE_VIEW_RESOURCE: {
        "name": "性能分析",
        "description": "使用 Trace 分析工作台进行日志分析与瓶颈定位。",
        "access_mode": "normal",
        "permissions": [PERFORMANCE_ACCESS_PERMISSION],
    },
    TEAM_VIEW_RESOURCE: {
        "name": "团队风采",
        "description": "查看团队成员、重点成果与贡献信息。",
        "access_mode": "normal",
        "permissions": [TEAM_ACCESS_PERMISSION],
    },
    DEMAND_VIEW_RESOURCE: {
        "name": "需求池",
        "description": "浏览、提交并支持平台共建需求。",
        "access_mode": "normal",
        "permissions": [DEMAND_ACCESS_PERMISSION],
    },
    USAGE_ANALYTICS_RESOURCE: {
        "name": "使用分析",
        "description": "查看平台使用趋势、用户明细与事件记录。",
        "access_mode": "admin",
        "permissions": [],
    },
    PERMISSION_MANAGE_RESOURCE: {
        "name": "权限管理",
        "description": "审批权限申请并配置资源访问策略。",
        "access_mode": "admin",
        "permissions": [],
    },
    ADMIN_MANAGE_RESOURCE: {
        "name": "管理员管理",
        "description": "配置管理员账号和管理员密码。",
        "access_mode": "admin",
        "permissions": [],
    },
}
