-- CreateTable
CREATE TABLE `users` (
    `id` INTEGER NOT NULL,
    `derivation_path` INTEGER NOT NULL AUTO_INCREMENT,
    `chain_id` VARCHAR(191) NULL,

    UNIQUE INDEX `users_derivation_path_key`(`derivation_path`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
