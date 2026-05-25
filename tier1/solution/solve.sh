#!/usr/bin/env bash
set -euo pipefail

chmod 755 /opt/aws-cli /opt/awsbin /opt/aws-cli/v2/current/bin/aws

cat > /app/awscli <<'EOWRAPPER'
#!/usr/bin/env bash
exec /opt/aws-cli/v2/current/bin/aws "$@"
EOWRAPPER
chmod 755 /app/awscli
