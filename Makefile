# ========================
# ft_wheel Project Makefile
# ========================

PROJECT_NAME = ft_wheel
SNAPSHOT_DIR = ./snapshots
TIMESTAMP   = $(shell date +"%Y%m%d_%H%M%S")

# List of volumes to snapshot (dynamically detected)
VOLUMES = $(shell docker volume ls --format "{{.Name}}" | grep "^$(PROJECT_NAME)_")

# ------------------------
# Default rules
# ------------------------

all: up

help:
	@echo "🎡 ft_wheel Project Commands:"
	@echo ""
	@echo "  📦 Docker Management:"
	@echo "    up              Start the project"
	@echo "    down            Stop the project"
	@echo "    logs            Show logs"
	@echo "    re              Full restart & cleaning (with snapshot backup)"
	@echo ""
	@echo "  💾 Snapshot Management:"
	@echo "    snapshot        Create snapshots of all volumes"
	@echo "    list-snapshots  List available snapshots"
	@echo "    verify-snapshots Verify integrity of all snapshots"
	@echo "    restore         Restore from latest snapshots"
	@echo "    restore-from    Restore from specific file (make restore-from FILE=filename.tar.gz)"
	@echo ""
	@echo "  🧹 Cleanup:"
	@echo "    clean           Remove dangling images"
	@echo "    clean-snapshots Keep only 5 most recent snapshots per volume"
	@echo "    fclean          Full cleanup with backup"
	@echo ""

.env:
	@echo "⚠️  You must fill the .env file before running 'make up'."

create-secrets:
	@echo "🔑 Generating docker secrets..."
	sh docker_secrets.sh

up: .env create-secrets
	@echo "🚀 Starting project with Docker Compose..."
	docker compose -p $(PROJECT_NAME) up --build -d

down:
	@echo "🛑 Stopping project..."
	docker compose -p $(PROJECT_NAME) down

logs:
	@echo "📜 Showing logs..."
	docker compose -p $(PROJECT_NAME) logs -f

# ------------------------
# Snapshot management
# ------------------------

snapshot:
	@echo "💾 Creating snapshots of volumes..."
	@echo "Volumes to backup: $(VOLUMES)"
	@mkdir -p $(SNAPSHOT_DIR)
	@if [ -z "$(VOLUMES)" ]; then \
		echo "⚠️ No volumes found for project $(PROJECT_NAME)"; \
		exit 0; \
	fi
	@# Create lock file to prevent concurrent snapshots
	@if [ -f "$(SNAPSHOT_DIR)/.snapshot_lock" ]; then \
		echo "⚠️ Another snapshot operation is in progress"; \
		exit 1; \
	fi
	@touch "$(SNAPSHOT_DIR)/.snapshot_lock"
	@trap 'rm -f "$(SNAPSHOT_DIR)/.snapshot_lock"' EXIT; \
	for vol in $(VOLUMES); do \
		echo " -> Saving volume $$vol"; \
		docker run --rm \
			-v "$$vol":/data:ro \
			-v "$(PWD)/$(SNAPSHOT_DIR)":/backup \
			busybox \
			tar czf "/backup/$$(echo "$$vol" | sed 's/$(PROJECT_NAME)_//')_$(TIMESTAMP).tar.gz" -C /data . || { \
				echo "❌ Failed to backup $$vol"; \
				rm -f "$(SNAPSHOT_DIR)/.snapshot_lock"; \
				exit 1; \
			}; \
	done
	@rm -f "$(SNAPSHOT_DIR)/.snapshot_lock"
	@echo "✅ Snapshots stored in $(SNAPSHOT_DIR)"

list-snapshots:
	@echo "📋 Available snapshots:"
	@ls -la $(SNAPSHOT_DIR)/ 2>/dev/null || echo "No snapshots found"

verify-snapshots:
	@echo "🔍 Verifying snapshot integrity..."
	@if [ ! -d "$(SNAPSHOT_DIR)" ]; then \
		echo "No snapshot directory found"; \
		exit 0; \
	fi
	@for snapshot in $(SNAPSHOT_DIR)/*.tar.gz; do \
		if [ -f "$$snapshot" ]; then \
			printf "Checking $$(basename $$snapshot)... "; \
			if tar tzf "$$snapshot" >/dev/null 2>&1; then \
				echo "✅ OK"; \
			else \
				echo "❌ CORRUPTED"; \
			fi; \
		fi; \
	done

restore:
	@echo "♻️ Restoring volumes from latest snapshots..."
	@if [ -z "$(VOLUMES)" ]; then \
		echo "⚠️ No volumes found for project $(PROJECT_NAME)"; \
		exit 1; \
	fi
	@for vol in $(VOLUMES); do \
		vol_short=$$(echo $$vol | sed 's/$(PROJECT_NAME)_//'); \
		LATEST=$$(ls -t $(SNAPSHOT_DIR)/$${vol_short}_*.tar.gz 2>/dev/null | head -n1); \
		if [ -z "$$LATEST" ]; then \
			echo " -> No snapshot found for $$vol (looking for $${vol_short}_*.tar.gz)"; \
		else \
			echo " -> Restoring $$vol from $$(basename $$LATEST)"; \
			docker run --rm \
				-v $$vol:/data \
				-v $(PWD)/$(SNAPSHOT_DIR):/backup \
				busybox \
				sh -c "rm -rf /data/* /data/.[^.]* 2>/dev/null || true && tar xzf /backup/$$(basename $$LATEST) -C /data"; \
		fi \
	done
	@echo "✅ Restore completed"

restore-from:
	@if [ -z "$(FILE)" ]; then \
		echo "Usage: make restore-from FILE=snapshot_file.tar.gz"; \
		exit 1; \
	fi
	@# Validate filename format and sanitize
	@case "$(FILE)" in \
		*[';|&$`"'\'']*) echo "❌ Invalid characters in filename"; exit 1;; \
		*_[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]_[0-9][0-9][0-9][0-9][0-9][0-9].tar.gz) ;; \
		*) echo "❌ Invalid filename format. Expected: name_YYYYMMDD_HHMMSS.tar.gz"; exit 1;; \
	esac
	@if [ ! -f "$(SNAPSHOT_DIR)/$(FILE)" ]; then \
		echo "❌ Snapshot file $(FILE) not found in $(SNAPSHOT_DIR)"; \
		exit 1; \
	fi
	@echo "♻️ Restoring from specific snapshot: $(FILE)"
	@# Extract volume name from filename (safer approach)
	@vol_name="$$(printf '%s\n' "$(FILE)" | sed 's/_[0-9]\{8\}_[0-9]\{6\}\.tar\.gz$$//')"; \
	full_vol="$(PROJECT_NAME)_$$vol_name"; \
	echo " -> Restoring to volume $$full_vol"; \
	docker run --rm \
		-v "$$full_vol":/data \
		-v "$(PWD)/$(SNAPSHOT_DIR)":/backup \
		busybox \
		sh -c "rm -rf /data/* /data/.[^.]* 2>/dev/null || true && tar xzf \"/backup/$(FILE)\" -C /data"
	@echo "✅ Restore completed"

# ------------------------
# Cleanup
# ------------------------

clean-snapshots:
	@echo "🧹 Cleaning old snapshots (keeping last 5)..."
	@if [ ! -d "$(SNAPSHOT_DIR)" ] || [ -z "$$(ls -A $(SNAPSHOT_DIR)/*.tar.gz 2>/dev/null)" ]; then \
		echo "No snapshots to clean"; \
		exit 0; \
	fi
	@for vol_type in $$(ls $(SNAPSHOT_DIR)/*_[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]_[0-9][0-9][0-9][0-9][0-9][0-9].tar.gz 2>/dev/null | sed 's/.*\///; s/_[0-9]\{8\}_[0-9]\{6\}\.tar\.gz$$//' | sort -u); do \
		echo " -> Cleaning $$vol_type snapshots"; \
		count=$$(ls -1 $(SNAPSHOT_DIR)/$${vol_type}_*.tar.gz 2>/dev/null | wc -l); \
		if [ "$$count" -gt 5 ]; then \
			ls -t $(SNAPSHOT_DIR)/$${vol_type}_*.tar.gz 2>/dev/null | tail -n +6 | while read file; do \
				echo "   Removing $$file"; \
				rm -f "$$file"; \
			done; \
		else \
			echo "   Only $$count snapshots, keeping all"; \
		fi; \
	done
	@echo "✅ Old snapshots cleaned"

clean: down
	@echo "🧹 Removing dangling images..."
	docker image prune -f

fclean:
	@echo "⚠️ Full cleanup with snapshot"
	$(MAKE) snapshot
	@echo "🔥 Removing containers, images, and volumes..."
	docker compose -p $(PROJECT_NAME) down --rmi all -v

re: fclean all
