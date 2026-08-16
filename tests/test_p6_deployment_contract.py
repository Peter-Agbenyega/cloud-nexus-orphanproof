from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEPLOY_SCRIPT = REPO_ROOT / "scripts" / "deploy_lambda_function_url.sh"


class P6DeploymentContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = DEPLOY_SCRIPT.read_text(encoding="utf-8")

    def assert_before(self, earlier: str, later: str) -> None:
        self.assertIn(earlier, self.source)
        self.assertIn(later, self.source)
        self.assertLess(self.source.index(earlier), self.source.index(later))

    def test_ca_validation_and_packaging_happen_before_ssm_put_parameter(self):
        self.assert_before("COCKROACH_CA_CERT_VALID=True", "aws ssm put-parameter")
        self.assert_before("LAMBDA_PACKAGE_BYTES=", "aws ssm put-parameter")
        self.assert_before("LOCAL_PACKAGE_VALIDATION=PASS", "aws ssm put-parameter")

    def test_script_uses_deployment_scoped_parameter_without_overwriting_base(self):
        self.assertIn(
            "/orphanproof/prod/database-url-deployments",
            self.source,
        )
        self.assertIn("DEPLOYMENT_PARAMETER_NAME", self.source)
        self.assertIn('"Overwrite": False', self.source)
        self.assertNotIn('"Overwrite": True', self.source)
        self.assertNotIn(
            'ORPHANPROOF_DATABASE_URL_PARAMETER_NAME:-/orphanproof/prod/database-url"',
            self.source,
        )

    def test_failed_cleanup_targets_only_new_deployment_parameter(self):
        self.assertIn("DEPLOYMENT_PARAMETER_CREATED", self.source)
        self.assertIn("LAMBDA_CONFIG_REFERENCES_DEPLOYMENT_PARAMETER", self.source)
        self.assertIn('--name "$DEPLOYMENT_PARAMETER_NAME"', self.source)
        self.assertNotIn('--name "$PARAMETER_NAME"', self.source)

    def test_lambda_environment_points_to_deployment_parameter_and_public_mode(self):
        self.assertIn(
            "ORPHANPROOF_DATABASE_URL_PARAMETER_NAME=$DEPLOYMENT_PARAMETER_NAME",
            self.source,
        )
        self.assertIn("ORPHANPROOF_PUBLIC_DEMO_ONLY=true", self.source)
        self.assertIn("ORPHANPROOF_BEDROCK_EMBEDDING_MODEL=local.feature-hash-v1", self.source)

    def test_function_url_cors_is_not_wildcard_post(self):
        self.assertNotIn("AllowOrigins=*", self.source)
        self.assertNotIn("AllowMethods=GET,POST", self.source)
        self.assertIn("AllowMethods=GET", self.source)


if __name__ == "__main__":
    unittest.main()
