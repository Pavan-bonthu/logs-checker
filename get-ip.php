<?php
/**
 * IT Log Tracker — Backend (upload.php)
 * Place this file alongside index.html on your Red Hat / Apache / Nginx + PHP server.
 * Base directory: /else/
 *
 * Actions handled (POST JSON or multipart):
 *   action=create_dir   → creates /else/{name}/{caseId}/
 *   action=upload_file  → uploads file(s) into /else/{name}/{caseId}/
 *   action=list_files   → lists files in /else/{name}/{caseId}/
 *   action=delete_file  → deletes a specific file
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, GET, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { http_response_code(200); exit; }

define('BASE_DIR', '/else/');

function safe_name($s) {
    // Allow only alphanumeric, dash, underscore, dot
    return preg_replace('/[^a-zA-Z0-9_\-\.]/', '_', $s);
}

function json_ok($data = []) {
    echo json_encode(array_merge(['ok' => true], $data));
    exit;
}

function json_err($msg) {
    http_response_code(400);
    echo json_encode(['ok' => false, 'error' => $msg]);
    exit;
}

// Parse action — from multipart or JSON body
$action = $_POST['action'] ?? null;
if (!$action) {
    $body = json_decode(file_get_contents('php://input'), true);
    $action = $body['action'] ?? null;
} else {
    $body = $_POST;
}

if (!$action) json_err('No action specified');

// ── CREATE DIRECTORY ────────────────────────────
if ($action === 'create_dir') {
    $name   = safe_name($body['name']   ?? '');
    $caseId = safe_name($body['caseId'] ?? '');
    if (!$name || !$caseId) json_err('name and caseId required');

    $dir = BASE_DIR . $name . '/' . $caseId . '/';
    if (!is_dir($dir)) {
        if (!mkdir($dir, 0755, true)) json_err('Failed to create directory: ' . $dir);
    }
    json_ok(['path' => $dir]);
}

// ── UPLOAD FILES ────────────────────────────────
if ($action === 'upload_file') {
    $name   = safe_name($body['name']   ?? '');
    $caseId = safe_name($body['caseId'] ?? '');
    if (!$name || !$caseId) json_err('name and caseId required');

    $dir = BASE_DIR . $name . '/' . $caseId . '/';
    if (!is_dir($dir)) {
        if (!mkdir($dir, 0755, true)) json_err('Directory does not exist and could not be created');
    }

    if (empty($_FILES)) json_err('No files received');

    $uploaded = [];
    $errors   = [];

    foreach ($_FILES as $key => $file) {
        // Handle both single and multiple file inputs
        $names = is_array($file['name']) ? $file['name'] : [$file['name']];
        $tmps  = is_array($file['tmp_name']) ? $file['tmp_name'] : [$file['tmp_name']];
        $errs  = is_array($file['error']) ? $file['error'] : [$file['error']];

        foreach ($names as $i => $origName) {
            if ($errs[$i] !== UPLOAD_ERR_OK) {
                $errors[] = $origName . ': upload error code ' . $errs[$i];
                continue;
            }
            $safeName = safe_name(basename($origName));
            // Prevent duplicate — append timestamp if exists
            $dest = $dir . $safeName;
            if (file_exists($dest)) {
                $info = pathinfo($safeName);
                $safeName = $info['filename'] . '_' . time() . (isset($info['extension']) ? '.' . $info['extension'] : '');
                $dest = $dir . $safeName;
            }
            if (move_uploaded_file($tmps[$i], $dest)) {
                $uploaded[] = ['name' => $safeName, 'path' => $dest, 'size' => filesize($dest)];
            } else {
                $errors[] = $origName . ': move failed';
            }
        }
    }

    if (empty($uploaded) && !empty($errors)) json_err(implode('; ', $errors));
    json_ok(['uploaded' => $uploaded, 'errors' => $errors, 'path' => $dir]);
}

// ── LIST FILES ──────────────────────────────────
if ($action === 'list_files') {
    $name   = safe_name($body['name']   ?? '');
    $caseId = safe_name($body['caseId'] ?? '');
    if (!$name || !$caseId) json_err('name and caseId required');

    $dir = BASE_DIR . $name . '/' . $caseId . '/';
    if (!is_dir($dir)) json_ok(['files' => [], 'path' => $dir]);

    $files = [];
    foreach (scandir($dir) as $f) {
        if ($f === '.' || $f === '..') continue;
        $fp = $dir . $f;
        $files[] = [
            'name'     => $f,
            'path'     => $fp,
            'size'     => filesize($fp),
            'modified' => date('Y-m-d H:i:s', filemtime($fp))
        ];
    }
    json_ok(['files' => $files, 'path' => $dir]);
}

// ── DELETE FILE ─────────────────────────────────
if ($action === 'delete_file') {
    $name     = safe_name($body['name']     ?? '');
    $caseId   = safe_name($body['caseId']   ?? '');
    $filename = safe_name($body['filename'] ?? '');
    if (!$name || !$caseId || !$filename) json_err('name, caseId, filename required');

    $fp = BASE_DIR . $name . '/' . $caseId . '/' . $filename;
    if (!file_exists($fp)) json_err('File not found');
    if (!unlink($fp)) json_err('Could not delete file');
    json_ok(['deleted' => $filename]);
}

json_err('Unknown action: ' . $action);
