import json
import os
import re
import subprocess as sp
import sys
from pathlib import Path

from cron_manager.config import CronConfig, CronTask


namespace_start_line_re = re.compile(r'\s*#\s*namespace\s+([^\s]+)\s+{\s+')
namespace_end_line_re   = re.compile(r'\s*#\s*namespace\s+([^\s]+)\s+}\s+')


def apply_config(args):
    cfg = CronConfig.from_yaml_file(args.config)
    current_canonical_cfg = _get_current_canonical_cfg()
    
    new_canonical_cfg = ''
    
    inside_namespace = False
    applied = False
    for line in current_canonical_cfg.split('\n'):
        line += '\n'
    
        match = namespace_start_line_re.fullmatch(line)
        if match is not None and match.group(1) == cfg.namespace:
            inside_namespace = True
            
        if not inside_namespace:
            new_canonical_cfg += line
            
        match = namespace_end_line_re.fullmatch(line)
        if match is not None and match.group(1) == cfg.namespace:
            new_canonical_cfg += cfg.to_canonical_conf()
            applied = True
            inside_namespace = False
    
    if not applied:
        new_canonical_cfg += cfg.to_canonical_conf()

    new_canonical_cfg = new_canonical_cfg.strip('\n') + '\n'

    _set_canonical_cfg(new_canonical_cfg)


def print_config(args):
    cfg = CronConfig.from_yaml_file(args.config)
    sys.stdout.write(json.dumps(cfg.model_dump(), indent=2))


def run_task(args):
    cfg = CronConfig.from_yaml_file(args.config)
    for task in cfg.tasks:
        if task.name == args.task_name:
            _launch_task(task)
            return

    raise RuntimeError(f'Task not found: {args.task_name}')


def _get_current_canonical_cfg() -> str:
    cmd = sp.run(['crontab', '-l'], stdout=sp.PIPE)
    if cmd.returncode != 0:
        return ''
    assert cmd.stdout is not None
    return cmd.stdout.decode('utf-8')


def _set_canonical_cfg(text: str):
    cmd = sp.run(['crontab', '-'], input=text.encode('utf-8'))
    cmd.check_returncode()


def _launch_task(task: CronTask):
    env = os.environ.copy()
    for name, value in task.env.items():
        env[name] = value
    cmd = sp.run(task.cmd, shell=True, env=env)
    cmd.check_returncode()
