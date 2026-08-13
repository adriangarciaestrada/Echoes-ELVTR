// Copyright Echoes of the Architects. All Rights Reserved.

using UnrealBuildTool;

public class Echoes : ModuleRules
{
	public Echoes(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		// Runtime-only dependencies. Editor-only modules must never be added
		// here: the packaged Linux/Windows game links this module.
		PublicDependencyModuleNames.AddRange(new string[]
		{
			"Core",
			"CoreUObject",
			"Engine",
			"InputCore",
			"EnhancedInput",
		});

		PrivateDependencyModuleNames.AddRange(new string[]
		{
		});
	}
}
