import galbot_sdk

cfg = {
    # 日志存放目录，如果为空，则默认生成在 ~/galbot_sdk_log/user_log
    "path": "",

    # 日志文件名，如果为空，则默认名称为 <process_name>_<current_time>_<pid>_<thread_id>.log
    "file_name": "",

    # 单个日志文件最大字节数，如果日志超过此大小，会切换到新文件
    "file_max_size": 10 * 1024 * 1024,  # 10MB

    # 循环日志文件最大数量，超过数量时会覆盖最旧的日志文件
    "file_max_num": 5,

    # 是否在控制台输出日志，默认 False
    "console_output": True,

    # 日志输出等级，可用值：debug, info, warning, error, critical
    "level": "info",
}

galbot_sdk.init_logger(cfg)

# 写日志
galbot_sdk.debug("Debug example")
galbot_sdk.info("Info example")
galbot_sdk.warning("Warning example")
galbot_sdk.error("Error example")
galbot_sdk.critical("Critical example")
