"""
Pipeline execution tests — verifies the data-loader process itself
runs successfully (exit code, no critical errors in output).
"""

import pytest


pytestmark = [pytest.mark.pipeline, pytest.mark.requires_emulator]


class TestPipelineExecution:

    def test_pipeline_exits_zero(self, pipeline_result):
        assert pipeline_result.returncode == 0, (
            f"ETL pipeline exited with code {pipeline_result.returncode}.\n"
            f"STDOUT:\n{pipeline_result.stdout}\n"
            f"STDERR:\n{pipeline_result.stderr}"
        )

    def test_pipeline_reports_completion(self, pipeline_result):
        assert "ETL PIPELINE COMPLETED SUCCESSFULLY" in pipeline_result.stdout, (
            "Expected completion message not found in pipeline output.\n"
            f"STDOUT:\n{pipeline_result.stdout}"
        )

    def test_pipeline_no_critical_errors(self, pipeline_result):
        stdout = pipeline_result.stdout
        # Critical errors cause an early exit — they appear before the summary
        assert "Cannot continue: Missing essential" not in stdout
        assert "Critical extraction errors" not in stdout

    def test_pipeline_extracted_products(self, pipeline_result):
        assert "1_product_data.csv" in pipeline_result.stdout, (
            "Pipeline output should mention 1_product_data.csv extraction"
        )

    def test_pipeline_loaded_all_collections(self, pipeline_result):
        stdout = pipeline_result.stdout
        for collection in ["PLProductContent", "PLCategory", "PLFeatureContent",
                           "PLVariant", "ProductIndexData", "CategoryRouting"]:
            assert collection in stdout, (
                f"Expected '{collection}' to appear in pipeline output"
            )

    def test_pipeline_verification_passed(self, pipeline_result):
        assert "Verification passed" in pipeline_result.stdout, (
            "Firestore verification step should pass after load"
        )
