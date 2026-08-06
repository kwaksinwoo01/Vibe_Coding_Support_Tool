# Company Word template lifecycle

## Purpose

The Word editor manages company Word templates as versioned assets instead of treating the user's current `Normal.dotm` as the only source of truth.

The initial company profiles are expected to be:

- **DCM electronic-document profile**: the default profile for electronic SOP and controlled documents.
- **FDM paper-document profile**: the profile used to author forms and SOP documents that are printed as controlled paper records.

Microsoft Word loads one user `Normal.dotm` from the user's Templates directory. Therefore DCM and FDM are stored as separate canonical profile files and only one profile is copied to the live Word `Normal.dotm` location at a time.

```text
%LOCALAPPDATA%/WordNormalStyleEditor/template-lifecycle/
├─ registry.json
├─ profiles/
│  ├─ dcm-electronic/
│  │  ├─ current/Normal.dotm
│  │  └─ versions/<version>/Normal.dotm
│  └─ fdm-.../
│     ├─ current/Normal.dotm
│     └─ versions/<version>/Normal.dotm
├─ assets/
│  └─ <asset-id>/
│     ├─ current/<template>.dotm|dotx
│     └─ versions/<version>/...
├─ reports/
├─ activation-backups/
└─ packages/
```

## Profile activation

1. The current active profile's canonical template is compared with the live `%APPDATA%/Microsoft/Templates/Normal.dotm`.
2. If the live template changed, activation is blocked.
3. The user chooses one action:
   - approve and save the live changes as a new version of the current profile;
   - discard the unapproved live changes;
   - cancel profile activation.
4. Word must be completely closed.
5. The live `Normal.dotm` is backed up.
6. The selected profile's canonical `Normal.dotm` is copied to the live Word location.

This prevents an FDM session from silently overwriting DCM changes, or the opposite.

## Preservation unit

The preservation unit is the **whole template file**, not a rebuilt style list.

Each approved version stores:

- the original `.dotm` or `.dotx` file;
- SHA-256 and file size;
- style snapshot and style-property changes;
- Building Block inventory;
- AutoText inventory;
- approval note and timestamp;
- change report.

Building Block inventory records the entry name, type, category, description, insertion option, content character count, and SHA-256 of the content string. The actual Building Block text is not copied into the JSON inventory. Its original content remains only inside the preserved template file.

Building Block and AutoText inventories are used to detect additions, removals, metadata changes, and Building Block content changes. The original file is retained because headers, Quick Parts, Building Blocks, VBA, custom UI, relationships, and other template content cannot be safely reconstructed from the style snapshot.

## Registered template assets

A user can register another `.dotm` or `.dotx` as a company template asset, including a header/document-building-block template.

Registration:

1. Copies the entire source template into the managed asset store.
2. Captures styles, Building Blocks, AutoText, file hash, and warnings.
3. Associates the asset with the currently active profile.
4. Includes the asset in that profile's distribution package.

A registered asset can be linked to multiple profiles. For example, one approved company header Building Block template can be shared by both the DCM electronic-document profile and the FDM paper-document profile without registering duplicate managed copies.

Update:

1. Compares the registered source path with the managed copy.
2. Displays a change report.
3. Saves the full report and a new managed version only after explicit user approval.

## Change validation

A template change report contains:

- full-file SHA-256 difference;
- style-property changes, including properties of added or removed styles;
- added, removed, metadata-changed, or content-changed Building Blocks;
- added and removed AutoText entries;
- inventory warnings when Word does not expose a template object.

A file-level hash difference is still considered a change even when the visible style or Building Block inventory is unchanged. This deliberately protects other `.dotm` package contents.

## Distribution package

A profile release ZIP contains:

```text
CompanyWordTemplate/
├─ Normal.dotm
├─ manifest.json
├─ Install-CompanyWordTemplate.ps1
├─ CompanyTemplates/
│  └─ registered .dotm/.dotx assets
└─ audit/
   ├─ profile.json
   ├─ normal-inventory.json
   ├─ normal-styles.json
   └─ assets/<asset-id>/
      ├─ asset.json
      └─ inventory.json
```

The manifest records profile identity, classification code, version, Normal.dotm SHA-256, style hash, Building Block count, AutoText count, asset hashes, and each asset's installation destination.

A package cannot be generated from an active profile while the live `Normal.dotm` contains unapproved changes. The user must first approve the changes or distribute the last approved canonical profile explicitly.

The package generator rejects two assets with the same file name in one profile because one ZIP member or employee installation target would overwrite the other.

The installer:

1. refuses to run while Word is open;
2. verifies the packaged `Normal.dotm` SHA-256;
3. backs up the employee's existing `Normal.dotm`;
4. installs the selected company `Normal.dotm`;
5. verifies every registered template asset SHA-256;
6. backs up an existing employee template before replacing a same-name asset;
7. installs `header-building-block-template` and `document-building-block-template` assets directly under `%APPDATA%/Microsoft/Word/STARTUP` so Word loads them as global templates at startup;
8. installs other company templates under `%APPDATA%/Microsoft/Templates/CompanyTemplates`.

## Operational rule

Direct edits in Word are allowed, but they are not silently accepted into the company standard. After saving `Normal.dotm` in Word, the user must use **현재 변경 검증·저장**. The approved version then becomes the canonical profile used for later activation and distribution.
