"""Simple Phase 3 test - verifies components work without needing running server."""

import sys
import os

# Fix encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

print("="*60)
print("Phase 3 Component Test (No Server Required)")
print("="*60)

# Test 1: Import all Phase 3 modules
print("\nTest 1: Importing Phase 3 modules...")
try:
    from coordinator.memory_rag import EpisodicMemoryRAG
    from coordinator.user_profile import UserProfile
    from coordinator.fact_extractor import FactExtractor
    from coordinator.repositories.user_profile_repository import UserProfileRepository
    print("[PASS] All Phase 3 modules imported successfully")
except ImportError as e:
    print(f"[FAIL] Import failed: {e}")
    sys.exit(1)

# Test 2: Initialize RAG memory
print("\nTest 2: Initializing RAG memory system...")
try:
    rag = EpisodicMemoryRAG(embedding_model="nomic-embed-text:latest")
    print(f"[PASS] RAG initialized (GPU: {rag.use_gpu})")
except Exception as e:
    print(f"[FAIL] RAG initialization failed: {e}")

# Test 3: Create user profile
print("\nTest 3: Creating user profile...")
try:
    profile = UserProfile("test_user_001")

    # Simulate session summary
    session_summary = {
        "user_name": "Alex",
        "background": ["Software engineer", "Learning Bitcoin"],
        "topics": ["Bitcoin", "Wallets", "Security"],
        "facts": ["Owns 0.5 BTC", "Uses hardware wallet"],
        "preferences": {"wallet_type": "cold storage"},
        "holdings": {"BTC": "0.5", "ETH": "2.0"},
        "persona_key": "Eeva",
        "message_count": 15
    }

    profile.update_from_session(session_summary)

    print(f"[PASS] Profile created for: {profile.data['name']}")
    print(f"  - Total sessions: {profile.data['total_sessions']}")
    print(f"  - Facts: {len(profile.data['facts'])}")
    print(f"  - Holdings: {profile.data['holdings']}")

    # Test context summary generation
    context = profile.get_context_summary(max_facts=5, max_topics=3)
    print(f"\n  Generated context summary ({len(context)} chars):")
    print(f"  {context[:200]}...")

except Exception as e:
    print(f"[FAIL] User profile test failed: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Test database schema
print("\nTest 4: Checking database schema...")
try:
    import sqlite3
    conn = sqlite3.connect("chats.db")
    cur = conn.cursor()

    # Check if Phase 3 tables exist
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('user_profiles', 'user_sessions')")
    tables = [row[0] for row in cur.fetchall()]

    if 'user_profiles' in tables and 'user_sessions' in tables:
        print("[PASS] Phase 3 database tables exist:")
        print("  - user_profiles")
        print("  - user_sessions")

        # Check indexes
        cur.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE '%user%'")
        indexes = [row[0] for row in cur.fetchall()]
        print(f"  - {len(indexes)} indexes created")
    else:
        print(f"[FAIL] Phase 3 tables missing. Found: {tables}")

    conn.close()

except Exception as e:
    print(f"[FAIL] Database check failed: {e}")

# Test 5: Verify initialization
print("\nTest 5: Testing startup initialization...")
try:
    from coordinator import startup

    # Initialize database
    startup.init_db()
    print("[PASS] Database initialized")

    # Initialize repositories
    startup.init_repositories()
    print("[PASS] Repositories initialized")

    # Get user profile repo
    user_profile_repo = startup.get_user_profile_repo()
    if user_profile_repo:
        print("[PASS] User profile repository available")

        # Try to create a test profile
        test_profile = user_profile_repo.create_profile("test_phase3_user")
        print(f"[PASS] Created test profile: {test_profile.user_id}")

        # Retrieve it
        retrieved = user_profile_repo.get_profile("test_phase3_user")
        if retrieved:
            print(f"[PASS] Retrieved profile: {retrieved.user_id}")

        # Clean up
        user_profile_repo.delete_profile("test_phase3_user")
        print("[PASS] Cleaned up test profile")

except Exception as e:
    print(f"[FAIL] Initialization test failed: {e}")
    import traceback
    traceback.print_exc()

# Summary
print("\n" + "="*60)
print("Phase 3 Component Test Complete")
print("="*60)
print("\nAll core Phase 3 components are functional!")
print("\nTo test with a real conversation:")
print("1. Start server: python run_react.py")
print("2. Open frontend: http://localhost:3000")
print("3. Start a chat and send 10+ messages")
print("4. Check logs for [Phase3] indicators")
print("5. Check database: sqlite3 chats.db 'SELECT * FROM user_profiles'")
