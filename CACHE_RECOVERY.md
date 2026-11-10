# Cache resume and recovery

The original cache database is `data/haysub.sqlite3`. It was not erased.
Earlier prompt-version changes made some saved chunks ineligible, and standalone
job source/progress previously lived only in memory. Keeping the database alone
did not guarantee that the next upload would restore that progress. Earlier
instructions promising that without checking were incomplete.

The application now checks the current cache and an explicitly compatible
`eastern-armenian-v1` cache when running `eastern-armenian-v2-cue-repair`.
It recomputes keys from **exact source cues, IDs, timestamps, adjacent context,
model and original prompt version**. It revalidates each result and never
restores English dialogue as Armenian. Unknown IDs, other models, other files,
different timestamps/contexts and unapproved prompt versions are not reused.
The original entries remain untouched, and legacy reuse is logged in SQLite's
`cache_reuse` table with the source key/version/model.

Uploading a file hydrates completed cues before any missing translations are
requested. The page reports **Պահված աշխատանքից վերականգնվել է N / total հատված**,
including how many came from the checked older version. Music-only cues are
completed silently. A partially restored chunk is processed if *any* cue is
missing, even if its first cue is already cached.

New standalone file jobs persist in the SQLite `file_jobs` table: source cues,
filename, model/prompt fingerprint, validated results and error/progress state.
The browser's remembered job ID can now restore progress after a server restart.
Click Retry to continue an interrupted job. Reuploading identical parsed content,
even under a different filename, reuses the same job for the same model/prompt.
If the model or prompt configuration changes, upload again to run the explicit
compatibility check instead of silently mixing incompatible results.

For jobs created *before* this change, the source might not exist in SQLite.
Upload the exact same SRT once after restarting the updated server. The restored
count will show what actually matches before missing work starts. Hash-only
cache entries cannot be safely associated with an unknown file just by their cue
numbers. The original 1,614-cue source was not found in saved video history or the
checked Downloads/Desktop locations, so the exact historical restored count has
not been verified against that file yet.

Tests cover old-version reuse with no Gemini call, rejection of changed source /
timestamps / context / model / unknown versions, original cache preservation,
resume after clearing process memory, renamed uploads, partial-chunk completion,
and immediate restored-progress display. No Gemini calls were made for this fix.
