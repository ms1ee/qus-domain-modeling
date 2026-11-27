"""Built-in default team building list and preset prize library."""

from __future__ import annotations

DEFAULT_LIST_LINES: list[str] = [
    # Technology Department
    "Zhang San;Technology Department",
    "Li Si;Technology Department",
    "Wang Wu;Technology Department",
    "Zhao Liu;Technology Department",
    # Product Department
    "Sun Qi;Product Department",
    "Zhou Ba;Product Department",
    "Wu Jiu;Product Department",
    "Zheng Shi;Product Department",
    # Cheng Ru Group
    "Feng Yi;Cheng Ru Group",
    "Chen Er;Cheng Ru Group",
    "Chu San;Cheng Ru Group",
    "Wei Si;Cheng Ru Group",
    # Marketing Department
    "Jiang Wu;Marketing Department",
    "Shen Liu;Marketing Department",
    "Han Qi;Marketing Department",
    "Yang Ba;Marketing Department",
    # Finance Department
    "Zhu Jiu;Finance Department",
    "Qin Shi;Finance Department",
    "You Yi;Finance Department",
    "Xu Er;Finance Department",
    # Human Resources Department
    "He San;Human Resources Department",
    "Lv Si;Human Resources Department",
    "Shi Wu;Human Resources Department",
    "Kong Liu;Human Resources Department",
]

# Each entry: (name, quantity, avoid_groups, associated_drawer)
DEFAULT_PRIZES: list[tuple[str, int, list[str], str | None]] = [
    ("Third Prize - Movie Tickets", 10, [], "Chen Qixian"),
    ("Second Prize - Shopping Cards", 5, [], "Jin Duo"),
    ("First Prize - 1 Day Annual Leave", 2, [], "Ma Jiaqi"),
]
