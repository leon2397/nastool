"""
fixes/ai/install_cuda.py - Install CUDA toolkit
"""

from ..base import Fix, FixResult
from ..registry import register_fix


@register_fix
class InstallCUDAFix(Fix):
    """Install CUDA toolkit for NVIDIA GPUs"""

    fix_id = "install_cuda"
    title = "Install CUDA Toolkit"
    description = "Install CUDA toolkit for NVIDIA GPU acceleration"
    risk = "high"
    requires_root = True

    def is_applicable(self) -> bool:
        """Check if NVIDIA GPU is present"""
        success, _ = self._run_command("nvidia-smi")
        return success

    def run(self) -> FixResult:
        """Install CUDA toolkit"""
        commands_run = []

        # Detect package manager
        has_apt = self._run_command("which apt")[0]
        has_yum = self._run_command("which yum")[0]

        if has_apt:
            # Ubuntu/Debian
            commands = [
                "apt update",
                "apt install -y nvidia-cuda-toolkit",
            ]
        elif has_yum:
            # CentOS/RHEL
            commands = [
                "yum install -y cuda-toolkit",
            ]
        else:
            return FixResult(
                fix_id=self.fix_id,
                success=False,
                message="Unsupported package manager. Install CUDA manually from nvidia.com",
                commands_run=commands_run,
            )

        # Run installation
        for cmd in commands:
            success, output = self._run_command(cmd, timeout=600)
            commands_run.append(cmd)

            if not success:
                return FixResult(
                    fix_id=self.fix_id,
                    success=False,
                    message=f"Failed to execute: {cmd}",
                    commands_run=commands_run,
                    output=output,
                )

        return FixResult(
            fix_id=self.fix_id,
            success=True,
            message="CUDA toolkit installed. Reboot recommended.",
            commands_run=commands_run,
        )
