// Copyright Echoes of the Architects. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Engine/DataTable.h"

#include "GameFeelRow.generated.h"

/**
 * One movement-feel tuning profile, imported from SourceAssets/DT_GameFeel.csv.
 *
 * Field names must match the CSV column headers exactly — that correspondence is
 * what the DataTable importer matches on, and a rename on either side silently
 * imports the column as zero.
 *
 * The defaults below mirror the CSV's `Default` row so the struct is usable
 * before the table is loaded, but the CSV is the source of truth: tuning happens
 * there, not here.
 *
 * Every field here drives something. A parameter that no longer has an effect is
 * removed from both sides rather than carried: a knob that does nothing costs
 * more than the column it saves.
 */
USTRUCT(BlueprintType)
struct FGameFeelRow : public FTableRowBase
{
	GENERATED_BODY()

	/** Ground movement speed, cm/s. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Feel|Movement")
	float WalkSpeed = 600.0f;

	/** Upward impulse applied on jump, cm/s. Fixed-height jump by design. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Feel|Jump")
	float JumpZVelocity = 700.0f;

	/** Multiplier on world gravity for this character. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Feel|Jump")
	float GravityScale = 2.0f;

	/** Fraction of ground control retained while airborne, 0-1. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Feel|Jump")
	float AirControl = 0.9f;

	/** Jumps allowed before landing. 2 = double jump. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Feel|Jump")
	int32 JumpMaxCount = 2;

	/** Window after landing in which a jump pressed mid-air still fires, seconds. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Feel|Jump")
	float InputBufferTime = 0.15f;

	/** Launch speed of the dodge, cm/s. Halved in air, which has no ground friction. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Feel|Dodge")
	float DodgeSpeed = 1500.0f;

	/** Total dodge duration, seconds. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Feel|Dodge")
	float DodgeDuration = 0.4f;

	/** Invulnerability window inside the dodge, seconds. Must not exceed DodgeDuration. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Feel|Dodge")
	float DodgeIFrameDuration = 0.25f;
};
