// Copyright Echoes of the Architects. All Rights Reserved.

#include "GameFeelComponent.h"

#include "Engine/DataTable.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"

DEFINE_LOG_CATEGORY_STATIC(LogGameFeel, Log, All);

namespace
{
	/** Fields written explicitly below; the name-matched pass must not repeat them. */
	bool IsHandledExplicitly(const FName& FieldName)
	{
		static const TSet<FName> Handled = {
			GET_MEMBER_NAME_CHECKED(FGameFeelRow, WalkSpeed),
			GET_MEMBER_NAME_CHECKED(FGameFeelRow, JumpZVelocity),
			GET_MEMBER_NAME_CHECKED(FGameFeelRow, GravityScale),
			GET_MEMBER_NAME_CHECKED(FGameFeelRow, AirControl),
			GET_MEMBER_NAME_CHECKED(FGameFeelRow, JumpMaxCount),
		};
		return Handled.Contains(FieldName);
	}
}

UGameFeelComponent::UGameFeelComponent()
{
	PrimaryComponentTick.bCanEverTick = false;
}

void UGameFeelComponent::BeginPlay()
{
	Super::BeginPlay();
	ApplyFeel();
}

bool UGameFeelComponent::ApplyFeel()
{
	AActor* Owner = GetOwner();
	if (!Owner)
	{
		return false;
	}

	if (!FeelTable)
	{
		UE_LOG(LogGameFeel, Warning,
			TEXT("%s: no feel table assigned; the character keeps its baked-in values."),
			*Owner->GetName());
		return false;
	}

	static const TCHAR* Context = TEXT("UGameFeelComponent::ApplyFeel");
	const FGameFeelRow* Row = FeelTable->FindRow<FGameFeelRow>(RowName, Context, /*bWarnIfMissing*/ false);
	if (!Row)
	{
		UE_LOG(LogGameFeel, Warning, TEXT("%s: row '%s' not found in %s."),
			*Owner->GetName(), *RowName.ToString(), *FeelTable->GetName());
		return false;
	}

	Feel = *Row;

	// An invulnerability window longer than the dodge it belongs to would leave
	// the character invulnerable after the dodge ends. Cheap to state, easy to
	// introduce by editing one column and not the other.
	if (Feel.DodgeIFrameDuration > Feel.DodgeDuration)
	{
		UE_LOG(LogGameFeel, Warning,
			TEXT("%s: DodgeIFrameDuration (%.3f) exceeds DodgeDuration (%.3f); "
				 "invulnerability will outlast the dodge."),
			*Owner->GetName(), Feel.DodgeIFrameDuration, Feel.DodgeDuration);
	}

	if (ACharacter* Character = Cast<ACharacter>(Owner))
	{
		ApplyToCharacter(*Character);
	}
	else
	{
		UE_LOG(LogGameFeel, Warning,
			TEXT("%s is not a Character; only the name-matched properties were applied."),
			*Owner->GetName());
	}

	const int32 Matched = ApplyToOwnerProperties(*Owner);

	UE_LOG(LogGameFeel, Log, TEXT("%s: applied row '%s' from %s (%d name-matched propert%s)."),
		*Owner->GetName(), *RowName.ToString(), *FeelTable->GetName(),
		Matched, Matched == 1 ? TEXT("y") : TEXT("ies"));

	return true;
}

void UGameFeelComponent::ApplyToCharacter(ACharacter& Character) const
{
	Character.JumpMaxCount = Feel.JumpMaxCount;

	if (UCharacterMovementComponent* Movement = Character.GetCharacterMovement())
	{
		Movement->MaxWalkSpeed = Feel.WalkSpeed;
		Movement->JumpZVelocity = Feel.JumpZVelocity;
		Movement->GravityScale = Feel.GravityScale;
		Movement->AirControl = Feel.AirControl;
	}
	else
	{
		UE_LOG(LogGameFeel, Warning, TEXT("%s has no movement component."),
			*Character.GetName());
	}
}

int32 UGameFeelComponent::ApplyToOwnerProperties(AActor& Owner) const
{
	const UScriptStruct* RowStruct = FGameFeelRow::StaticStruct();
	UClass* OwnerClass = Owner.GetClass();
	int32 Applied = 0;

	for (TFieldIterator<FProperty> It(RowStruct); It; ++It)
	{
		const FProperty* Source = *It;
		const FName FieldName = Source->GetFName();
		if (IsHandledExplicitly(FieldName))
		{
			continue;
		}

		const void* SourceValue = Source->ContainerPtrToValuePtr<void>(&Feel);
		double Value = 0.0;
		if (const FFloatProperty* AsFloat = CastField<FFloatProperty>(Source))
		{
			Value = static_cast<double>(AsFloat->GetPropertyValue(SourceValue));
		}
		else if (const FIntProperty* AsInt = CastField<FIntProperty>(Source))
		{
			Value = static_cast<double>(AsInt->GetPropertyValue(SourceValue));
		}
		else
		{
			continue;
		}

		FProperty* Target = OwnerClass->FindPropertyByName(FieldName);
		if (!Target)
		{
			UE_LOG(LogGameFeel, Warning,
				TEXT("%s: row field '%s' has no property of that name on %s; it is "
					 "tuning nothing."),
				*Owner.GetName(), *FieldName.ToString(), *OwnerClass->GetName());
			continue;
		}

		void* TargetValue = Target->ContainerPtrToValuePtr<void>(&Owner);
		if (FDoubleProperty* AsDouble = CastField<FDoubleProperty>(Target))
		{
			// Blueprint float variables are doubles; the row's are floats.
			AsDouble->SetPropertyValue(TargetValue, Value);
		}
		else if (FFloatProperty* AsFloat = CastField<FFloatProperty>(Target))
		{
			AsFloat->SetPropertyValue(TargetValue, static_cast<float>(Value));
		}
		else if (FIntProperty* AsInt = CastField<FIntProperty>(Target))
		{
			AsInt->SetPropertyValue(TargetValue, static_cast<int32>(Value));
		}
		else
		{
			UE_LOG(LogGameFeel, Warning,
				TEXT("%s: '%s' exists on %s but is a %s, not a number; skipped."),
				*Owner.GetName(), *FieldName.ToString(), *OwnerClass->GetName(),
				*Target->GetClass()->GetName());
			continue;
		}

		UE_LOG(LogGameFeel, Verbose, TEXT("%s: %s = %g"),
			*Owner.GetName(), *FieldName.ToString(), Value);
		++Applied;
	}

	return Applied;
}
