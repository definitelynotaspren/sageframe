from pathlib import Path
import frontmatter
from llama_cpp import Llama
import time
from typing import List, Dict
import datetime
import json

# === CONFIGURATION ===
vault_path = Path(r"INSERT PATH HERE")
LOG_FILE = vault_path / "glyph_assignments.jsonl"  # Using JSON Lines format

# Initialize logging file if needed
if not LOG_FILE.exists():
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("")  # Create empty file

def log_assignment(filename: str, glyphs: list, action: str, error: str = None):
    """Log assignments in JSON Lines format"""
    entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "file": filename,
        "action": action,
        "glyphs": glyphs,
        "run_id": datetime.datetime.now().strftime("%Y%m%d-%H%M%S"),
        "error": error
    }
    
    with open(LOG_FILE, "a", encoding="utf-8") as log:
        log.write(json.dumps(entry) + "\n")

# Expanded Glyph Lexicon with Permission Glyph
GLYPH_LEXICON = {
    "⟁": {
        "name": "Paradox Glyph",
        "meanings": ["paradox", "complex systems", "collapse", "fragmentation", "ambiguous truth"],
        "archetypes": ["The Trickster", "The Puzzle", "The Labyrinth"],
        "requires_permission": False
    },
    "⚯": {
        "name": "Dual Witness Glyph",
        "meanings": ["witnessing", "mirroring", "trauma", "grief", "duality", "entanglement"],
        "archetypes": ["The Twins", "The Mirror", "The Echo"],
        "requires_permission": False
    },
    "∷": {
        "name": "Recursion Glyph",
        "meanings": ["loops", "recursion", "patterns", "iteration", "self-reference"],
        "archetypes": ["The Ouroboros", "The Fractal", "The Algorithm"],
        "requires_permission": False
    },
    "∞": {
        "name": "Eternal Glyph",
        "meanings": ["memory", "eternity", "cycles", "immortality", "permanence"],
        "archetypes": ["The Ancient", "The Monument", "The Timeless"],
        "requires_permission": False
    },
    "🜁": {
        "name": "Breath Glyph",
        "meanings": ["breath", "spirit", "transformation", "air", "alchemy"],
        "archetypes": ["The Wind", "The Phoenix", "The Alchemist"],
        "requires_permission": False
    },
    "⧖": {
        "name": "Temporal Fold",
        "meanings": ["time dilation", "deja vu", "temporal distortion"],
        "archetypes": ["The Timekeeper", "The Prophet"],
        "requires_permission": True  # Special glyph requiring permission
    },
    "⁂": {
        "name": "Threshold Marker",
        "meanings": ["initiation", "portals", "boundary crossing"],
        "archetypes": ["The Gatekeeper", "The Wanderer"],
        "requires_permission": True
    }
}

# LLM Configuration
llm = Llama(
    model_path=r"INSERT PATH HERE",
    n_ctx=4096,
    n_threads=8,
    n_gpu_layers=40  # Enable if you have GPU
)

def generate_glyph_prompt(is_personal_stream: bool = True) -> str:
    """Dynamically creates the LLM prompt with configurable rules"""
    glyph_descriptions = []
    for glyph, data in GLYPH_LEXICON.items():
        desc = f"{glyph} ({data['name']}): {', '.join(data['meanings'])}. Archetypes: {', '.join(data['archetypes'])}"
        if data["requires_permission"]:
            desc += " [REQUIRES PERMISSION]"
        glyph_descriptions.append(desc)
    
    rule_set = (
        "- Max 3 glyphs for personal streams\n"
        "- Max 7 glyphs for shared experiences (must include permission glyph)\n"
        "- Permission glyphs: ⧖, ⁂"
    ) if not is_personal_stream else "- Max 3 glyphs for personal streams"
    
    return f"""Analyze the text and select glyphs that best represent its core themes.
    
Available Glyphs:
{" | ".join(glyph_descriptions)}

Rules:
{rule_set}

Return ONLY glyph characters separated by commas."""

def validate_glyphstream(glyphs: List[str], is_personal: bool = True) -> List[str]:
    """Enforces glyph assignment rules"""
    valid_glyphs = [g for g in glyphs if g in GLYPH_LEXICON]
    
    # Check permission requirements for shared streams
    if not is_personal:
        permission_glyphs = {g for g, data in GLYPH_LEXICON.items() if data["requires_permission"]}
        if not any(g in permission_glyphs for g in valid_glyphs):
            return []  # Reject entire stream if no permission glyph
        
    # Apply length limits
    max_glyphs = 3 if is_personal else 7
    return valid_glyphs[:max_glyphs]

def llm_assign_glyphs(text: str, is_personal_stream: bool = True) -> List[str]:
    if len(text) < 100:
        return []
    
    try:
        response = llm.create_chat_completion(
            messages=[{
                "role": "system",
                "content": generate_glyph_prompt(is_personal_stream)
            }, {
                "role": "user",
                "content": f"Analyze this text for glyph assignment:\n\n{text[:3000]}"
            }],
            temperature=0.4,
            max_tokens=50
        )
        
        raw_glyphs = response['choices'][0]['message']['content'].strip()
        candidate_glyphs = [g.strip() for g in raw_glyphs.split(",")]
        return validate_glyphstream(candidate_glyphs, is_personal_stream)
                
    except Exception as e:
        print(f"LLM Error: {e}")
        return []

# Processing Loop
for i, md_file in enumerate(vault_path.rglob("*.md")):
    try:
        post = frontmatter.load(md_file)
        
        # Skip if already processed (unless force_update=True)
        if 'glyphstream' in post.metadata:
            log_assignment(md_file.name, [], "SKIPPED")
            continue
            
        print(f"Analyzing {md_file.name}...")
        
        # Determine stream type (default to personal)
        is_personal = "shared_experience" not in post.metadata.get("tags", [])
        glyphstream = llm_assign_glyphs(post.content, is_personal)
        
        if glyphstream:
            # Build rich metadata
            glyph_metadata = {
                glyph: {
                    "name": GLYPH_LEXICON[glyph]["name"],
                    "meanings": GLYPH_LEXICON[glyph]["meanings"],
                    "archetypes": GLYPH_LEXICON[glyph]["archetypes"],
                    "requires_permission": GLYPH_LEXICON[glyph]["requires_permission"]
                } for glyph in glyphstream
            }
            
            post.metadata.update({
                'glyphstream': glyphstream,
                'glyph_metadata': glyph_metadata,
                'last_processed': datetime.datetime.now().isoformat(),
                'stream_type': 'personal' if is_personal else 'shared'
            })
            
            with open(md_file, 'w', encoding='utf-8') as f:
                frontmatter.dump(post, f)
            
            log_assignment(md_file.name, glyphstream, "UPDATED")
            print(f"[✓] Assigned {len(glyphstream)} glyphs to {md_file.name}")
            
        else:
            log_assignment(md_file.name, [], "NO_MATCH")
            
        time.sleep(0.5)  # Gentle rate limiting
        
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        log_assignment(md_file.name, [], "ERROR", error_msg)
        print(f"[!] Failed on {md_file.name}: {error_msg}")

# Final report
print(f"\nProcessing complete. Log saved to {LOG_FILE}")