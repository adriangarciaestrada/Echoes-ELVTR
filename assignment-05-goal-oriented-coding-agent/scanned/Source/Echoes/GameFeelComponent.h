// Copyright Echoes of the Architects. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"

#include "GameFeelRow.h"

#include "GameFeelComponent.generated.h"

/**
 * Applies a movement-feel row from DT_GameFeel to its owning character on play.
 *
 * Before this existed the CSV was documentation: its numbers matched the values
 * baked into the character's movement component because someone kept them in
 * step by hand, and editing the CSV changed nothing in the game. This is the
 * mechanism that makes the table authoritative.
 *
 * It lives in C++ for two reasons. The routing rule puts anything a compiler can
 * check on this side, and the four values that matter most — walk speed, jump
 * impulse, gravity scale, air control — are properties of the movement
 * component, which cannot be written from a Blueprint graph authored through the
 * editor bridge.
 *
 * Add it to a character, point it at the table, and it applies on BeginPlay.
 * Components begin play before the owning actor's BeginPlay event, so the values
 * are in place before any Blueprint logic reads them.
 */
UCLASS(ClassGroup = (Echoes), meta = (BlueprintSpawnableComponent))
class ECHOES_API UGameFeelComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UGameFeelComponent();

	/** The table to read. Normally /Game/Data/DT_GameFeel. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Feel")
	TObjectPtr<UDataTable> FeelTable;

	/** Which row. One profile per class once the second class exists. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Feel")
	FName RowName = FName(TEXT("Default"));

	/** The row that was applied, readable by Blueprint logic that needs it. */
	UPROPERTY(BlueprintReadOnly, Category = "Feel")
	FGameFeelRow Feel;

	/**
	 * Read the row and apply it. Called on BeginPlay; exposed so tuning can be
	 * re-applied at runtime after a reimport without leaving play.
	 *
	 * @return false if the table or row is missing, having changed nothing.
	 */
	UFUNCTION(BlueprintCallable, Category = "Feel")
	bool ApplyFeel();

protected:
	virtual void BeginPlay() override;

private:
	/** Walk speed, jump impulse, gravity, air control, jump count. */
	void ApplyToCharacter(class ACharacter& Character) const;

	/**
	 * Copies any remaining row field onto a property of the owner with the same
	 * name — the Blueprint's own dodge and input-buffer variables.
	 *
	 * Name matching is the contract the whole seam already runs on: the CSV
	 * columns match the struct fields by name, checked before every import, and
	 * this is that correspondence carried one step further. Every field is
	 * logged as applied or unmatched, so a rename shows up in the log rather
	 * than as a value that quietly stops updating.
	 *
	 * @return how many properties were written.
	 */
	int32 ApplyToOwnerProperties(AActor& Owner) const;
};
