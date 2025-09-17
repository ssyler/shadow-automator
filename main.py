#!/usr/bin/env python3
import os
import shutil
from datetime import datetime
from pathlib import Path

# 🎩 ShadowAutomator: organize files magically

# Terminal colors
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def organize_folder(folder):
    report = []
    counts = {}
    for item in os.listdir(folder):
        path = os.path.join(folder, item)
        if os.path.isfile(path):
            ext = Path(item).suffix.lower().replace('.', '')
            if not ext:
                ext = 'other'
            dest_dir = os.path.join(folder, ext)
            os.makedirs(dest_dir, exist_ok=True)
            new_path = os.path.join(dest_dir, item)
            shutil.move(path, new_path)
            report.append(f"{item} -> {ext}/")
            counts[ext] = counts.get(ext, 0) + 1
    return report, counts

def print_report(report, counts):
    print(f"\n{bcolors.OKCYAN}✨ Files moved:{bcolors.ENDC}")
    for line in report:
        print(f"  {bcolors.OKGREEN}{line}{bcolors.ENDC}")
    print(f"\n{bcolors.HEADER}📊 Summary by type:{bcolors.ENDC}")
    for ext, num in counts.items():
        print(f"  {bcolors.OKBLUE}{ext}: {num}{bcolors.ENDC}")

def main():
    folder_input = input(f"{bcolors.BOLD}Enter the path of the folder to tame: {bcolors.ENDC}").strip()
    folder = os.path.expanduser(folder_input)
    if os.path.exists(folder) and os.path.isdir(folder):
        print(f"\n{bcolors.OKCYAN}🧙‍♂️ Organizing '{folder}'...\n{bcolors.ENDC}")
        report, counts = organize_folder(folder)
        print_report(report, counts)

        # Save report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(folder, f"shadow_report_{timestamp}.txt")
        with open(report_file, "w") as f:
            f.write("\n".join(report))
        print(f"\n{bcolors.OKGREEN}✅ Done! Folder '{folder}' is now organized. Report saved as {report_file}{bcolors.ENDC}\n")
        print(f"{bcolors.WARNING}🎉 Share your magical folder transformations with friends!{bcolors.ENDC}")
    else:
        print(f"{bcolors.FAIL}❌ Invalid folder path. Try again.{bcolors.ENDC}")

if __name__ == "__main__":
    main()
