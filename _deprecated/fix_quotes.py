# -*- coding: utf-8 -*-
import os
fix_path = os.path.join(os.getcwd(), "sagan_auto_apply.py")
s = open(fix_path, encoding="utf-8").read()
s = s.replace('df["field_name\'].unique()', "df['field_name'].unique()")
open(fix_path, "w", encoding="utf-8").write(s)
print("corrigido")
