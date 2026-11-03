import os
import random
from datetime import datetime, timedelta
import subprocess

def create_commits(start_date, end_date, username, email):
    """
    Create backdated commits from start_date to end_date
    """
    current_date = start_date
    commit_count = 0
    
    # Create a file to modify
    commit_file = "commit_history.txt"
    
    while current_date <= end_date:
        # Random number of commits per day (0-5)
        num_commits = random.randint(0, 5)
        
        for i in range(num_commits):
            # Add random hours and minutes to the date
            commit_time = current_date + timedelta(
                hours=random.randint(9, 20),
                minutes=random.randint(0, 59)
            )
            
            # Format the date for git
            date_str = commit_time.strftime("%Y-%m-%d %H:%M:%S")
            
            # Write to file
            with open(commit_file, "a") as f:
                f.write(f"Commit on {date_str}\n")
            
            # Stage the file
            subprocess.run(["git", "add", commit_file], check=True)
            
            # Set environment variables for git commit date
            env = os.environ.copy()
            env['GIT_AUTHOR_DATE'] = date_str
            env['GIT_COMMITTER_DATE'] = date_str
            
            # Create commit with backdated timestamp
            commit_message = f"Update on {current_date.strftime('%Y-%m-%d')}"
            subprocess.run(
                ["git", "commit", "-m", commit_message],
                env=env,
                check=True
            )
            
            commit_count += 1
            print(f"Created commit #{commit_count} for {date_str}")
        
        # Move to next day
        current_date += timedelta(days=1)
    
    print(f"\n✅ Total commits created: {commit_count}")
    print(f"\n⚠️  To push these commits to GitHub, run:")
    print(f"   git push origin main --force")

if __name__ == "__main__":
    # Configuration
    START_DATE = datetime(2024, 1, 1)
    END_DATE = datetime(2024, 3, 1)
    
    # Replace with your GitHub details
    USERNAME = "soul-abhi"
    EMAIL = "your-email@example.com"  # Update this with your GitHub email
    
    print("🚀 Starting commit generation...")
    print(f"📅 Date range: {START_DATE.date()} to {END_DATE.date()}")
    print(f"👤 Username: {USERNAME}\n")
    
    # Check if we're in a git repository
    try:
        subprocess.run(["git", "status"], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        print("❌ Error: Not a git repository. Run 'git init' first.")
        exit(1)
    
    # Configure git user if needed
    subprocess.run(["git", "config", "user.name", USERNAME], check=True)
    subprocess.run(["git", "config", "user.email", EMAIL], check=True)
    
    try:
        create_commits(START_DATE, END_DATE, USERNAME, EMAIL)
    except KeyboardInterrupt:
        print("\n\n⚠️  Process interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
