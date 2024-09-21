/*
  Warnings:

  - You are about to drop the column `buy_token_address` on the `users` table. All the data in the column will be lost.
  - You are about to drop the column `buy_token_name` on the `users` table. All the data in the column will be lost.
  - You are about to drop the column `sell_token_address` on the `users` table. All the data in the column will be lost.
  - You are about to drop the column `sell_token_name` on the `users` table. All the data in the column will be lost.

*/
-- AlterTable
ALTER TABLE `users` DROP COLUMN `buy_token_address`,
    DROP COLUMN `buy_token_name`,
    DROP COLUMN `sell_token_address`,
    DROP COLUMN `sell_token_name`,
    ADD COLUMN `token0_address` VARCHAR(191) NULL,
    ADD COLUMN `token0_name` VARCHAR(191) NULL,
    ADD COLUMN `token1_address` VARCHAR(191) NULL,
    ADD COLUMN `token1_name` VARCHAR(191) NULL;
