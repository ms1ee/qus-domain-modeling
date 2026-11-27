"""Built-in default team building participant list and preset prize library."""

# (name, department group)
DEFAULT_PARTICIPANTS = [
    ("Chen Qixian", "Technology Department"),
    ("Zhang Wei", "Technology Department"),
    ("Liu Yang", "Technology Department"),
    ("Wang Lei", "Technology Department"),
    ("Zhao Min", "Product Department"),
    ("Jin Duo", "Product Department"),
    ("Sun Hao", "Product Department"),
    ("Zhou Ting", "Product Department"),
    ("Ma Jiaqi", "Operations Department"),
    ("Xu Ying", "Operations Department"),
    ("Hu Jun", "Operations Department"),
    ("Guo Fang", "Operations Department"),
    ("Li Bin", "Marketing Department"),
    ("He Na", "Marketing Department"),
    ("Gao Peng", "Marketing Department"),
    ("Lin Xiao", "Marketing Department"),
    ("Cheng Ming", "Cheng Ru Group"),
    ("Song Yu", "Cheng Ru Group"),
    ("Tang Hui", "Cheng Ru Group"),
    ("Feng Rui", "Cheng Ru Group"),
    ("Han Bo", "Human Resources Department"),
    ("Deng Yan", "Human Resources Department"),
    ("Cao Jing", "Human Resources Department"),
    ("Peng Tao", "Human Resources Department"),
]

# (name, quantity, avoid_groups, associated_drawer)
DEFAULT_PRIZES = [
    ("Third Prize - Movie Tickets", 5, [], "Chen Qixian"),
    ("Second Prize - Shopping Cards", 3, ["Product Department"], "Jin Duo"),
    ("First Prize - 1 Day Annual Leave", 1, [], "Ma Jiaqi"),
]
