-- CreateTable
CREATE TABLE `users` (
    `id` INTEGER NOT NULL,
    `derivation_path` VARCHAR(191) NOT NULL,
    `chain_id` VARCHAR(191) NULL,

    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
