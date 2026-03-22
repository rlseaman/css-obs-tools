#!/usr/bin/tclsh
#
# wamo-test.tcl — offline test suite for wamo's trackstat parser
#
# Test vectors extracted from live MPC responses captured during
# CSS observing runs across all five active telescopes, 2026.
#
# Run: tclsh wamo-test.tcl
# Or:  tclsh /path/to/wamo-test.tcl
#
# Tests the trackstat proc in isolation — no network calls.

# Source the wamo script to get access to trackstat and whazzit
# We need to prevent it from executing main — source only the procs.
# Since wamo doesn't guard main with a proc, we extract what we need.

# --- Inline the required procs from wamo ---

proc whazzit { instr } {
    if {[string equal $instr "verified"] }         { return "mixed observations, to be split and assigned to appropriate queues" }
    if {[string equal $instr "neo/new/incoming"] } { return "new NEOCP or PCCP objects" }
    if {[string equal $instr "neocp/incoming"] }   { return "NEOCP or PCCP followup" }
    if {[string equal $instr "neo/mopp"] }         { return "unnumbered NEOs" }
    if {[string equal $instr "neo/num"] }          { return "numbered NEOs" }
    if {[string equal $instr "neo/newid"] }        { return "NEO (p)recoveries" }
    if {[string equal $instr "mba/itf"] }          { return "unidentified tracklets heading to the Isolated Tracklet File (ITF)" }
    if {[string equal $instr "mba/mopp"] }         { return "unnumbered MBAs" }
    if {[string equal $instr "mba/num"] }          { return "numbered MBAs" }
    if {[string equal $instr "mba/new"] }          { return "possible new MBAs to be designated" }
    if {[string equal $instr "mba/newid"] }        { return "MBA (p)recoveries" }
    if {[string equal $instr "newcode"] }          { return "observations awaiting a program code to be assigned" }
    if {[string equal $instr "tno/unn"] }          { return "unnumbered one-opposition TNOs" }
    if {[string equal $instr "tno/mopp"] }         { return "unnumbered multi-opposition TNOs" }
    if {[string equal $instr "tno/num"] }          { return "numbered TNOs" }
    if {[string equal $instr "tno/newid"] }        { return "TNO (p)recoveries" }
    if {[string equal $instr "tno/new"] }          { return "possible new TNOs to be designated" }
    if {[string equal $instr "sat/unn"] }          { return "unnumbered natural satellites" }
    if {[string equal $instr "sat/num"] }          { return "numbered natural satellites" }
    if {[string equal $instr "sat/new"] }          { return "possible new natural satellites to be designated" }
    if {[string equal $instr "cmt/cmt"] }          { return "unnumbered comets" }
    if {[string equal $instr "cmt/pct"] }          { return "numbered comets" }
    if {[string equal $instr "cmt/new"] }          { return "possible new comets (but not on PCCP -- e.g. SOHO or archival data)" }
    if {[string equal $instr "artsat"] }           { return "artsat processing queue" }
    if {[string equal $instr "sat/art"] }          { return "artificial satellite processing queue" }
    if {[string equal $instr "sat"] }              { return "natural satellite processing queue" }
    if {[string equal $instr "problems"] }         { return "flagged for manual review" }
    return "unrecognized, try wamo -v and see https://minorplanetcenter.net/beta/help.html"
}

# Source trackstat from the actual wamo script
set wamo_dir [file dirname [info script]]
set wamo_path [file join $wamo_dir wamo]
if {![file exists $wamo_path]} {
    set wamo_path "wamo"
}

# Extract trackstat proc by finding "proc trackstat" through its closing "}"
set fd [open $wamo_path r]
set lines [split [read $fd] "\n"]
close $fd

set in_proc 0
set depth 0
set proc_lines {}
foreach line $lines {
    if {!$in_proc && [string match "proc trackstat *" $line]} {
	set in_proc 1
    }
    if {$in_proc} {
	lappend proc_lines $line
	# Count braces
	foreach ch [split $line ""] {
	    if {$ch eq "\{"} { incr depth }
	    if {$ch eq "\}"} { incr depth -1 }
	}
	if {$depth == 0 && [llength $proc_lines] > 1} {
	    break
	}
    }
}
if {!$in_proc} { puts "ERROR: cannot find trackstat in $wamo_path"; exit 1 }
eval [join $proc_lines "\n"]

# --- Test framework ---

set pass 0
set fail 0
set total 0

proc test { name desig utdate raw_response expected_status } {
    global pass fail total
    global utdate_g
    set utdate_g $utdate

    # trackstat uses global utdate
    uplevel #0 [list set utdate $utdate]

    set result [trackstat $desig $raw_response]

    incr total
    if {$result eq $expected_status} {
	incr pass
    } else {
	incr fail
	puts "FAIL: $name"
	puts "  expected: $expected_status"
	puts "  got:      $result"
	puts ""
    }
}

# --- Test vectors ---
# Each test: name, designation, utdate, raw MPC response, expected parsed status

puts "Running wamo trackstat tests...\n"

# === trkSub format statuses ===

test "trkSub: not a minor planet" \
    "C4634Q1" "2026 03 22" \
    "The trkSub 'C4634Q1 703' (LtKBny2Y0000BqW5010000001) is not a minor planet.\nThe trkSub 'C4634Q1 703' (LtKBny2Y0000BqW5010000002) is not a minor planet.\nThe trkSub 'C4634Q1 703' (LtKBny2Y0000BqW5010000003) is not a minor planet." \
    "is not a minor planet"

test "trkSub: deleted" \
    "C1D3MD5" "2026 03 21" \
    "The trkSub 'C1D3MD5 V00' (LtK5cF1s0000BqT4010000001) has been deleted.\nThe trkSub 'C1D3MD5 V00' (LtK5cF1s0000BqT4010000002) has been deleted.\nThe trkSub 'C1D3MD5 V00' (LtK5cF1s0000BqT4010000003) has been deleted." \
    "was deleted"

test "trkSub: artificial" \
    "C45ZEM1" "2026 03 08" \
    "The trkSub 'C45ZEM1 703' (Lt77h75k0000Boeh010000001) was suspected to be artificial.\nThe trkSub 'C45ZEM1 703' (Lt77h75k0000Boeh010000002) was suspected to be artificial.\nThe trkSub 'C45ZEM1 703' (Lt77h75k0000Boeh010000003) was suspected to be artificial.\nThe trkSub 'C45ZEM1 703' (Lt77h75k0000Boeh010000004) was suspected to be artificial." \
    "was suspected to be artificial"

test "trkSub: near-duplicate" \
    "ST26CA4" "2026 03 21" \
    "The trkSub 'ST26CA4 I52' (LtK91r4j0000BqUq010000001) was flagged as a near-duplicate.\nThe trkSub 'ST26CA4 I52' (LtK91r4j0000BqUq010000002) was flagged as a near-duplicate.\nThe trkSub 'ST26CA4 I52' (LtK91r4j0000BqUq010000003) was flagged as a near-duplicate.\nThe trkSub 'ST26CA4 I52' (LtK91r4j0000BqUq010000004) was flagged as a near-duplicate." \
    "was flagged as a near-duplicate"

test "trkSub: not been processed" \
    "CEFEQ52" "2026 03 22" \
    "The trkSub 'CEFEQ52 I52' (LtL7YI5M0000BqcX010000001) has not been processed.\nThe trkSub 'CEFEQ52 I52' (LtL7YI5M0000BqcX010000002) has not been processed.\nThe trkSub 'CEFEQ52 I52' (LtL7YI5M0000BqcX010000003) has not been processed." \
    "has been received, but not processed"

test "trkSub: queued neo/new/incoming" \
    "CEF3A92" "2026 03 21" \
    "The trkSub 'CEF3A92 G96' (LtK5rkC80000BqTF010000001) is in the 'neo/new/incoming' processing queue.\nThe trkSub 'CEF3A92 G96' (LtK5rkC80000BqTF010000002) is in the 'neo/new/incoming' processing queue.\nThe trkSub 'CEF3A92 G96' (LtK5rkC80000BqTF010000003) is in the 'neo/new/incoming' processing queue." \
    "has been queued to neo/new/incoming (new NEOCP or PCCP objects)"

test "trkSub: queued sat/art" \
    "CEF4A62" "2026 03 21" \
    "The trkSub 'CEF4A62 G96' (LtK7BLEb0000BqTm010000001) is in the 'sat/art' processing queue.\nThe trkSub 'CEF4A62 G96' (LtK7BLEb0000BqTm010000002) is in the 'sat/art' processing queue.\nThe trkSub 'CEF4A62 G96' (LtK7BLEb0000BqTm010000003) is in the 'sat/art' processing queue.\nThe trkSub 'CEF4A62 G96' (LtK7BLEb0000BqTm010000004) is in the 'sat/art' processing queue." \
    "has been queued to sat/art (artificial satellite processing queue)"

test "trkSub: queued artsat" \
    "C463MT1" "2026 03 22" \
    "The trkSub 'C463MT1 703' (LtL8S62k0000Bqd7010000001) is in the 'artsat' processing queue.\nThe trkSub 'C463MT1 703' (LtL8S62k0000Bqd7010000002) is in the 'artsat' processing queue.\nThe trkSub 'C463MT1 703' (LtL8S62k0000Bqd7010000003) is in the 'artsat' processing queue.\nThe trkSub 'C463MT1 703' (LtL8S62k0000Bqd7010000004) is in the 'artsat' processing queue." \
    "has been queued to artsat (artsat processing queue)"

test "trkSub: queued cmt/pct" \
    "C463L41" "2026 03 22" \
    "The trkSub 'C463L41 703' (LtLBrX020000BqeO010000001) is in the 'cmt/pct' processing queue.\nThe trkSub 'C463L41 703' (LtLBrX020000BqeO010000002) is in the 'cmt/pct' processing queue.\nThe trkSub 'C463L41 703' (LtLBrX020000BqeO010000003) is in the 'cmt/pct' processing queue.\nThe trkSub 'C463L41 703' (LtLBrX020000BqeO010000004) is in the 'cmt/pct' processing queue." \
    "has been queued to cmt/pct (numbered comets)"

test "trkSub: queued neocp/incoming" \
    "C463MF1" "2026 03 22" \
    "The trkSub 'C463MF1 I52' (LtL8Ju2X0000Bqcw010000001) is in the 'neocp/incoming' processing queue.\nThe trkSub 'C463MF1 I52' (LtL8Ju2X0000Bqcw010000002) is in the 'neocp/incoming' processing queue.\nThe trkSub 'C463MF1 I52' (LtL8Ju2X0000Bqcw010000003) is in the 'neocp/incoming' processing queue.\nThe trkSub 'C463MF1 I52' (LtL8Ju2X0000Bqcw010000004) is in the 'neocp/incoming' processing queue." \
    "has been queued to neocp/incoming (NEOCP or PCCP followup)"

test "trkSub: queued mba/itf" \
    "C463MD1" "2026 03 22" \
    "The trkSub 'C463MD1 I52' (LtL8KRBY0000Bqcx010000001) is in the 'mba/itf' processing queue.\nThe trkSub 'C463MD1 I52' (LtL8KRBY0000Bqcx010000002) is in the 'mba/itf' processing queue.\nThe trkSub 'C463MD1 I52' (LtL8KRBY0000Bqcx010000003) is in the 'mba/itf' processing queue.\nThe trkSub 'C463MD1 I52' (LtL8KRBY0000Bqcx010000004) is in the 'mba/itf' processing queue." \
    "has been queued to mba/itf (unidentified tracklets heading to the Isolated Tracklet File (ITF))"

test "trkSub: queued mba/mopp" \
    "C1DAXW5" "2026 03 22" \
    "The trkSub 'C1DAXW5 V00' (LtL6d3Fj0000Bqc0010000001) is in the 'mba/mopp' processing queue.\nThe trkSub 'C1DAXW5 V00' (LtL6d3Fj0000Bqc0010000002) is in the 'mba/mopp' processing queue.\nThe trkSub 'C1DAXW5 V00' (LtL6d3Fj0000Bqc0010000003) is in the 'mba/mopp' processing queue.\nThe trkSub 'C1DAXW5 V00' (LtL6d3Fj0000Bqc0010000004) is in the 'mba/mopp' processing queue." \
    "has been queued to mba/mopp (unnumbered MBAs)"

# === obs80 format statuses ===

test "obs80: NEOCP" \
    "C1D0PR5" "2026 03 20" \
    "     C1D0PR5*1C2026 03 20.34236115 02 21.980+24 21 10.91               V     V00 (LtJ8tY1P0000BqMs010000001) is on the NEOCP/PCCP.\n     C1D0PR5 1C2026 03 20.34802015 02 21.721+24 21 28.66         23.92GV     V00 (LtJ8tY1P0000BqMs010000002) is on the NEOCP/PCCP.\n     C1D0PR5 1C2026 03 20.35361215 02 21.494+24 21 45.36               V     V00 (LtJ8tY1P0000BqMs010000003) is on the NEOCP/PCCP.\n     C1D0PR5 1C2026 03 20.35919815 02 21.239+24 22 02.86         22.86GV     V00 (LtJ8tY1P0000BqMs010000004) is on the NEOCP/PCCP." \
    "is on the NEOCP"

test "obs80: published" \
    "C45ZE41" "2026 03 08" \
    "     K26E02R*1C2026 03 08.29259009 33 14.780-22 00 52.90         18.49GVEE141703 (Lt76vV060000BoeL010000001) has been identified as 2026 ER2 and published in MPEC 2026-E141.\n     K26E02R 1C2026 03 08.29494509 33 24.610-22 02 19.10         18.43GVEE141703 (Lt76vV060000BoeL010000002) has been identified as 2026 ER2 and published in MPEC 2026-E141.\n     K26E02R 1C2026 03 08.29729909 33 34.410-22 03 46.10         18.52GVEE141703 (Lt76vV060000BoeL010000003) has been identified as 2026 ER2 and published in MPEC 2026-E141.\n     K26E02R 1C2026 03 08.29965109 33 44.330-22 05 12.60         18.67GVEE141703 (Lt76vV060000BoeL010000004) has been identified as 2026 ER2 and published in MPEC 2026-E141." \
    "was published"

test "obs80: pending publication" \
    "C461DM1" "2026 03 17" \
    "A0058        1C2026 03 17.31769111 31 55.380+02 30 33.52         17.86GV     703 (LtGBpZBV0000Bpsl0100000XU) has been identified as (100058), publication is pending.\nA0058        1C2026 03 17.31999311 31 55.254+02 30 37.48         18.10GV     703 (LtGBpZBV0000Bpsl0100000XV) has been identified as (100058), publication is pending.\nA0058        1C2026 03 17.32229711 31 55.146+02 30 42.16         17.97GV     703 (LtGBpZBV0000Bpsl0100000XW) has been identified as (100058), publication is pending.\nA0058        1C2026 03 17.32459911 31 55.038+02 30 46.12         17.99GV     703 (LtGBpZBV0000Bpsl0100000XX) has been identified as (100058), publication is pending." \
    "is pending publication"

test "obs80: ITF" \
    "C1CHY25" "2026 02 25" \
    "     C1CHY25 1C2026 02 25.40664113 36 47.772+08 09 36.58               V     V00 (Lst9aABm0000Bndd010000001) has been placed in the Isolated Tracklet File (ITF).\n     C1CHY25 1C2026 02 25.41223113 36 44.104+08 08 46.97         21.55GV     V00 (Lst9aABm0000Bndd010000002) has been placed in the Isolated Tracklet File (ITF).\n     C1CHY25 1C2026 02 25.41782213 36 40.478+08 07 57.65         21.28GV     V00 (Lst9aABm0000Bndd010000003) has been placed in the Isolated Tracklet File (ITF).\n     C1CHY25 1C2026 02 25.42340913 36 36.817+08 07 08.29         21.48GV     V00 (Lst9aABm0000Bndd010000004) has been placed in the Isolated Tracklet File (ITF)." \
    "is in the ITF"

# === Cross-date: obs80 with observations on different date than utdate ===

test "obs80: published on prior date (cross-date visibility)" \
    "C1D0QJ5" "2026 03 22" \
    "     K26F03B 1C2026 03 21.24148013 38 35.567+29 15 56.34         21.27GVEF130I52 (LtK5rX2f0000BqTE010000001) has been identified as 2026 FB3 and published in MPEC 2026-F130.\n     K26F03B 1C2026 03 21.24346713 38 35.275+29 15 27.83         21.02GVEF130I52 (LtK5rX2f0000BqTE010000002) has been identified as 2026 FB3 and published in MPEC 2026-F130.\n     K26F03B 1C2026 03 21.24545013 38 34.937+29 14 59.39               VEF130I52 (LtK5rX2f0000BqTE010000003) has been identified as 2026 FB3 and published in MPEC 2026-F130.\n     K26F03B 1C2026 03 21.24743013 38 34.634+29 14 30.08         20.93GVEF130I52 (LtK5rX2f0000BqTE010000004) has been identified as 2026 FB3 and published in MPEC 2026-F130." \
    "was published"

test "obs80: published + pending (multi-date, published wins)" \
    "C1D0QJ5" "2026 03 22" \
    "     K26F03B 1C2026 03 21.24148013 38 35.567+29 15 56.34         21.27GVEF130I52 (LtK5rX2f0000BqTE010000001) has been identified as 2026 FB3 and published in MPEC 2026-F130.\n     K26F03B 1C2026 03 22.35816213 36 08.341+23 40 02.46         20.37GV     I52 (LtLBOM620000Bqe7010000001) has been identified as 2026 FB3, publication is pending." \
    "was published"

# === Explicit MPC responses ===

test "explicit: not found by MPC" \
    "ZZZZZZZ" "2026 03 22" \
    "\"ZZZZZZZ 703\" was not found after attempting a search." \
    "was not found by MPC"

test "explicit: invalid identifier" \
    "-q" "2026 03 21" \
    "-q G96 was not identified as a valid observation identifier." \
    "is not a valid identifier"

# === Empty response ===

test "empty: no MPC response" \
    "BOGUS01" "2026 03 22" \
    "" \
    "no MPC response"

# === Mixed: published takes priority over NEOCP (multi-date) ===

test "obs80: NEOCP today + published prior (published wins)" \
    "CEF53C2" "2026 03 21" \
    "     K26F03A 1C2026 03 20.33278212 13 53.216-08 16 56.35         21.16GVEF129G96 (LtKLtQ880000BqZa010000001) has been identified as 2026 FA3 and published in MPEC 2026-F129.\n     K26F03A*1C2026 03 21.32279012 05 59.006-10 30 41.36         20.88GVEF129G96 (LtK7uY4u0000BqUF010000001) has been identified as 2026 FA3 and published in MPEC 2026-F129." \
    "was published"

# --- Results ---

puts ""
puts [format "Results: %d passed, %d failed, %d total" $pass $fail $total]

if {$fail > 0} {
    exit 1
} else {
    puts "All tests passed."
    exit 0
}
