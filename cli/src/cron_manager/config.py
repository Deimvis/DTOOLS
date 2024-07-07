import datetime
import yaml
from pathlib import Path
from pydantic import BaseModel, Field, field_validator
from cron_validator import CronValidator


class CronTask(BaseModel):
    name: str
    schedule_expr: str
    cmd: str
    env: dict[str, str] = Field(default_factory=dict)
    
    @field_validator('schedule_expr')
    @classmethod
    def is_valid_cron_schedule_expr(cls, v):
        assert CronValidator.parse(v) is not None
        return v
    
    def to_canonical_conf_task(self) -> str:
        builder = CanonicalCronConfigBuilder()
        builder.comment_line(f'task: {self.name}')
        for name, value in self.env.items():
            builder.env_line(name, value)
        builder.cmd_line(self.schedule_expr, self.cmd)
        return builder.build()


class CronConfig(BaseModel):
    namespace: str
    global_env: dict[str, str] = Field(default_factory=dict)
    tasks: list[CronTask]

    def to_canonical_conf(self) -> str:
        s = '#'
        builder = CanonicalCronConfigBuilder()
        builder.comment_line(f'namespace {self.namespace} {{')
        builder.comment_line(f'(last update: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})')
        builder.blank_line()
        for name, value in self.global_env.items():
            builder.env_line(name, value)
        if len(self.global_env) > 0:
            builder.blank_line()
        builder.raw('\n'.join(map(lambda t: t.to_canonical_conf_task(), self.tasks)))
        builder.blank_line()
        builder.comment_line(f'namespace {self.namespace} }}')
        return builder.build()

    @staticmethod
    def from_yaml_file(file_path: str) -> 'CronConfig':
        with Path(file_path).open() as f:
            data = yaml.safe_load(f)
        return CronConfig.model_validate(data)

        
class CanonicalCronConfigBuilder:
    def __init__(self):
        self.text = ''
    
    def cmd_line(self, schedule_expr: str, cmd: str) -> str:
        self.text += f'{schedule_expr} {cmd}\n'
    
    def env_line(self, env_name: str, env_value: str):
        self.text += f'{env_name}={env_value}\n'
    
    def comment_line(self, line: str):
        self.text += f'# {line}\n'
    
    def blank_line(self):
        self.text += '\n'
    
    def raw(self, s: str):
        self.text += s
    
    def build(self) -> str:
        return self.text