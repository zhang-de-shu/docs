claude --dangerously-skip-permissions

export HTTPS_PROXY="http://127.0.0.1:7890"

# zenmux
export ANTHROPIC_BASE_URL="https://zenmux.ai/api/anthropic"

export ANTHROPIC_BASE_URL="http://47.108.176.183:9000"
export ANTHROPIC_AUTH_TOKEN="sk-ai-v1-bf4bfd0a73a49dd3e3f3ebebf95d6c2e99082ea070c7a3cc4e60af78fff8402d"
export CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1

export ANTHROPIC_API_KEY="sk-ai-v1-bf4bfd0a73a49dd3e3f3ebebf95d6c2e99082ea070c7a3cc4e60af78fff8402d"


# SF_ccr
export ANTHROPIC_BASE_URL=https://claudecode.sf-express.com/ccr/
export ANTHROPIC_AUTH_TOKEN=01450616
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
export CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1

# SF-效能
export ANTHROPIC_BASE_URL="http://llm-model-hub-apis.sf-express.com"
export ANTHROPIC_AUTH_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3NLZXkiOiJhcGkyXzQzYTQxNjIzLTFhODktNGUyMy1iNzhjLTA3M2ExMWRmMWFlMiIsImVudiI6InByZCIsImp0aSI6MzE5NjksInByb2plY3RfaWQiOjE3NDg4LCJzeXN0ZW1LZXkiOiI2M2ZlYWUwMy04NGMzLTQxNjUtOGU4OS1mZjEzM2Q4MzMxNmIifQ.2EpWuV7vAgi4Z1inZeSjsMrvMBcV5DtRd0XJ79K3iNo"
export ANTHROPIC_MODEL=claude/claude-opus-4-6
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
export CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1
export CLAUDE_CODE_DISABLE_THINKING=1

## 咸鱼
export ANTHROPIC_BASE_URL="http://cccai.cfd"
export ANTHROPIC_AUTH_TOKEN="sk-mkVIYCgEsjDQcLNF2zj6SX4mo37XyjjmQmZodbclTc8xXH2E"
export CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1

Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3NLZXkiOiJhcGkyX2Q0ZDZkM2MwLTMyYTYtNDc3Ni05ZWY1LWU2MzEwOTFkMjBiOCIsImVudiI6IiIsImp0aSI6MjEwODcsInByb2plY3RfaWQiOjExNjc2LCJzeXN0ZW1LZXkiOiI5MzIyZTMwMS1mYTI4LTRiMTQtYmQyNC04MzQ3Mzc1NWIzODAifQ.A-x86tdUlzUjhZb2sKZDwHGe49Zkx_wEkKH8C4MvUAs

# 个人
export ANTHROPIC_BASE_URL="http://llm-model-hub-apis.sf-express.com"
export ANTHROPIC_AUTH_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3NLZXkiOiJhcGkyX2Q0ZDZkM2MwLTMyYTYtNDc3Ni05ZWY1LWU2MzEwOTFkMjBiOCIsImVudiI6IiIsImp0aSI6MjEwODcsInByb2plY3RfaWQiOjExNjc2LCJzeXN0ZW1LZXkiOiI5MzIyZTMwMS1mYTI4LTRiMTQtYmQyNC04MzQ3Mzc1NWIzODAifQ.A-x86tdUlzUjhZb2sKZDwHGe49Zkx_wEkKH8C4MvUAs"
export ANTHROPIC_MODEL="claude/claude-opus-4-6"
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
export CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1
export CLAUDE_CODE_DISABLE_THINKING=1


curl -v --location --request GET 'http://model-square.sf-express.com/v1/api/model-center/projects/personal/quota?emp_num=01450616' \
--header 'x-sf-userid: 01450616'

curl -v --location --request GET 'http://model-square.sf-express.com/v1/api/model-center/projects/personal/quota?emp_num=01386718' \
--header 'x-sf-userid: 01386718'



