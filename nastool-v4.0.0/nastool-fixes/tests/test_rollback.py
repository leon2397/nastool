# -*- coding: utf-8 -*-
"""Test rollback mechanism for nastool-fixes"""
import sys
import os
import tempfile
import shutil

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_rollback_status_enum():
    """Test RollbackStatus enum"""
    from nastool_fixes.base import RollbackStatus

    assert RollbackStatus.NOT_NEEDED.value == "not_needed"
    assert RollbackStatus.SUCCESSFUL.value == "successful"
    assert RollbackStatus.FAILED.value == "failed"
    assert RollbackStatus.NOT_SUPPORTED.value == "not_supported"


def test_fix_result_rollback_fields():
    """Test FixResult has rollback fields"""
    from nastool_fixes.base import FixResult, RollbackStatus

    result = FixResult(
        fix_id="test_fix",
        success=True,
        message="Test message",
        rollback_status=RollbackStatus.SUCCESSFUL,
        rollback_message="Rollback successful"
    )

    assert result.rollback_status == RollbackStatus.SUCCESSFUL
    assert result.rollback_message == "Rollback successful"


def test_rollback_info():
    """Test RollbackInfo dataclass"""
    from nastool_fixes.base import RollbackInfo, RollbackStatus
    from datetime import datetime

    info = RollbackInfo(
        fix_id="test_fix",
        timestamp=datetime.now().isoformat(),
        original_state={"key": "value"},
        backup_files=["/path/to/backup"],
        rollback_commands=["rm /path/to/file"],
        status=RollbackStatus.SUCCESSFUL,
        message="Test message"
    )

    assert info.fix_id == "test_fix"
    assert info.status == RollbackStatus.SUCCESSFUL
    assert len(info.backup_files) == 1


def test_fix_supports_rollback_flag():
    """Test Fix supports_rollback flag"""
    from nastool_fixes.base import Fix

    class TestFix(Fix):
        fix_id = "test_fix"
        title = "Test Fix"
        supports_rollback = True

        def is_applicable(self) -> bool:
            return True

        def run(self):
            from nastool_fixes.base import FixResult
            return FixResult(self.fix_id, True, "Test")

    fix = TestFix()
    assert fix.supports_rollback is True


def test_fix_unsupported_rollback():
    """Test Fix without rollback support"""
    from nastool_fixes.base import Fix, RollbackStatus

    class TestFixNoRollback(Fix):
        fix_id = "test_fix_no_rollback"
        title = "Test Fix No Rollback"
        supports_rollback = False

        def is_applicable(self) -> bool:
            return True

        def run(self):
            from nastool_fixes.base import FixResult
            return FixResult(self.fix_id, True, "Test")

    fix = TestFixNoRollback()
    result = fix.rollback()

    assert result.success is False
    assert result.rollback_status == RollbackStatus.NOT_SUPPORTED


def test_create_rollback_result():
    """Test create_rollback_result helper function"""
    from nastool_fixes.base import create_rollback_result, RollbackStatus

    result = create_rollback_result(
        fix_id="test_fix",
        success=True,
        message="Rollback successful",
        status=RollbackStatus.SUCCESSFUL
    )

    assert result.success is True
    assert result.rollback_status == RollbackStatus.SUCCESSFUL


def test_fix_backup_and_restore():
    """Test Fix backup and restore methods"""
    from nastool_fixes.base import Fix

    class TestFix(Fix):
        fix_id = "test_backup_fix"
        title = "Test Backup Fix"
        supports_rollback = False

        def is_applicable(self) -> bool:
            return True

        def run(self):
            from nastool_fixes.base import FixResult
            return FixResult(self.fix_id, True, "Test")

    fix = TestFix()

    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("test content")
        temp_file = f.name

    try:
        backup_path = fix._create_backup(temp_file)
        assert backup_path is not None
        assert os.path.exists(backup_path)

        with open(temp_file, 'r') as f:
            original_content = f.read()

        with open(backup_path, 'r') as f:
            backup_content = f.read()

        assert original_content == backup_content

        restored = fix._restore_backup(backup_path, temp_file)
        assert restored is True

        with open(temp_file, 'r') as f:
            restored_content = f.read()

        assert original_content == restored_content

    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)
        if backup_path and os.path.exists(backup_path):
            os.remove(backup_path)


def test_fix_capture_state():
    """Test Fix _capture_state method"""
    from nastool_fixes.base import Fix

    class TestFix(Fix):
        fix_id = "test_capture_fix"
        title = "Test Capture Fix"
        supports_rollback = False

        def is_applicable(self) -> bool:
            return True

        def run(self):
            from nastool_fixes.base import FixResult
            return FixResult(self.fix_id, True, "Test")

    fix = TestFix()

    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("test content for capture")
        temp_file = f.name

    try:
        state = fix._capture_state(temp_file)
        assert state is not None

        import json
        state_data = json.loads(state)
        assert state_data['type'] == 'file'
        assert state_data['path'] == temp_file
        assert state_data['content'] == "test content for capture"

    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)


if __name__ == "__main__":
    tests = [
        test_rollback_status_enum,
        test_fix_result_rollback_fields,
        test_rollback_info,
        test_fix_supports_rollback_flag,
        test_fix_unsupported_rollback,
        test_create_rollback_result,
        test_fix_backup_and_restore,
        test_fix_capture_state,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            print(f"[PASS] {test.__name__}")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {test.__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\nResults: {passed} passed, {failed} failed")
