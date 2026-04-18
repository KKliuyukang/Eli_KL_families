(function () {
  const raw = window.APP_DATA || { families: [] };

  const palette = [
    { bg: "var(--blue-bg)", text: "var(--blue-text)" },
    { bg: "var(--coral-bg)", text: "var(--coral-text)" },
    { bg: "var(--teal-bg)", text: "var(--teal-text)" },
    { bg: "var(--violet-bg)", text: "var(--violet-text)" },
    { bg: "var(--pink-bg)", text: "var(--pink-text)" },
  ];

  const searchInput = document.getElementById("search-input");
  const familyGrid = document.getElementById("family-grid");
  const addFamilyButton = document.getElementById("add-family-button");
  const modal = document.getElementById("family-modal");
  const modalContent = document.getElementById("modal-content");
  const lightbox = document.getElementById("image-lightbox");
  const lightboxImage = document.getElementById("lightbox-image");

  let families = normalizeFamilies(raw.families || []);
  let selectedFamilyId = null;

  function normalizeFamilies(items) {
    return items.map((family, index) => {
      const parents = family.parents || [];
      const inferredMother = parents[0] || null;
      const inferredFather = parents[1] || null;
      const childHints = family.background?.memory_hints || [];
      const tags = buildTags(family);

      return {
        id: family.id,
        colorIndex: index % palette.length,
        child: {
          name_en: family.child?.name || "Unknown child",
          name_zh: family.child?.name_zh || "",
          photo_url: fileUrl(family.child?.profile_image),
          birthday: extractBirthday(childHints),
          tags,
          class_name: "KL 2026",
        },
        father: {
          name: inferredFather?.name || "",
          photo_url: fileUrl(
            inferredFather?.profile_image ||
              family.galleries?.father?.[0] ||
              family.galleries?.parent?.[1] ||
              ""
          ),
          phone: "",
          email: "",
        },
        mother: {
          name: inferredMother?.name || "",
          photo_url: fileUrl(
            inferredMother?.profile_image ||
              family.galleries?.mother?.[0] ||
              family.galleries?.parent?.[0] ||
              ""
          ),
          phone: "",
          email: "",
        },
        notes: buildNotes(family),
        custom_fields: {
          whatsapp_names: family.whatsapp_names || [],
          evidence: family.evidence || [],
          memory_hints: childHints,
        },
      };
    });
  }

  function buildTags(family) {
    const tags = [];
    if (family.tags?.includes("chat-extracted")) tags.push("群聊整理");
    if (family.galleries?.family?.length) tags.push("有家庭照");
    if ((family.whatsapp_names || []).length) tags.push(`群名 ${family.whatsapp_names[0]}`);
    return tags.slice(0, 4);
  }

  function buildNotes(family) {
    const parts = [];
    if (family.notes?.length) parts.push(...family.notes);
    if (family.background?.memory_hints?.length) parts.push(...family.background.memory_hints);
    if (!parts.length && family.evidence?.[0]?.text) parts.push(`来自群聊：${family.evidence[0].text}`);
    return parts.join("\n");
  }

  function extractBirthday(hints) {
    const birthdayHint = (hints || []).find((item) => /\b20\d{2}[-/]\d{2}\b/.test(item));
    if (!birthdayHint) return "";
    const match = birthdayHint.match(/\b(20\d{2}[-/]\d{2})\b/);
    return match ? match[1].replace("/", "-") : "";
  }

  function fileUrl(path) {
    if (!path) return "";
    const normalized = path.replace(/^\.?\//, "");
    const pathname = window.location.pathname || "";
    const prefix = pathname.includes("/app/") || pathname.endsWith("/app") ? "../" : "./";
    return `${prefix}${normalized}`;
  }

  function familySearchBlob(family) {
    return [
      family.child.name_en,
      family.child.name_zh,
      family.father.name,
      family.mother.name,
      family.notes,
      ...(family.custom_fields.whatsapp_names || []),
    ]
      .join(" ")
      .toLowerCase();
  }

  function filteredFamilies() {
    const query = searchInput.value.trim().toLowerCase();
    if (!query) return families;
    return families.filter((family) => familySearchBlob(family).includes(query));
  }

  function getPalette(index) {
    return palette[index % palette.length];
  }

  function firstLetter(name) {
    return (name || "?").trim().slice(0, 1).toUpperCase();
  }

  function silhouetteSvg() {
    return `
      <svg class="silhouette" viewBox="0 0 24 24" aria-hidden="true">
        <circle cx="12" cy="8" r="4" fill="currentColor"></circle>
        <path d="M5 19c0-3.2 2.8-5 7-5s7 1.8 7 5" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"></path>
      </svg>
    `;
  }

  function avatarMarkup(options) {
    const { name, photoUrl, sizeClass, placeholderLabel, paletteIndex, completelyUnknown } = options;
    const color = getPalette(paletteIndex);

    if (photoUrl) {
      return `
        <span
          class="avatar-photo-trigger"
          data-photo-url="${photoUrl}"
          data-photo-name="${escapeAttribute(name || "")}"
          role="button"
          tabindex="0"
          aria-label="查看${escapeAttribute(name || "头像")}原图"
        >
          <div class="avatar ${sizeClass}"><img src="${photoUrl}" alt="${name || ""}" /></div>
        </span>
      `;
    }

    if (name && !completelyUnknown) {
      const textClass = sizeClass.includes("child") ? "avatar-text-child" : "avatar-text-parent";
      return `
        <div class="avatar ${sizeClass} avatar--initial" style="background:${color.bg}; color:${color.text};">
          <span class="avatar-text ${textClass}">${firstLetter(name)}</span>
        </div>
      `;
    }

    const inner = placeholderLabel ? `<span class="avatar-text avatar-text-parent">${placeholderLabel}</span>` : silhouetteSvg();
    return `<div class="avatar ${sizeClass} avatar--placeholder">${inner}</div>`;
  }

  function parentCardMarkup(role, parent, paletteIndex) {
    const placeholder = role === "爸爸" ? "爸" : "妈";
    return `
      <div class="parent-mini-card">
        ${avatarMarkup({
          name: parent.name,
          photoUrl: parent.photo_url,
          sizeClass: "avatar-parent",
          placeholderLabel: placeholder,
          paletteIndex,
          completelyUnknown: !parent.name,
        })}
        <div class="parent-role">${role}</div>
        <div class="parent-name">${nameTriggerMarkup(parent.name)}</div>
      </div>
    `;
  }

  function nameTriggerMarkup(name) {
    if (!name) return "\u00a0";
    return `
      <span
        class="name-audio-trigger"
        data-pronounce="${escapeAttribute(name)}"
        role="button"
        tabindex="0"
        aria-label="朗读 ${escapeAttribute(name)}"
      >
        ${escapeHtml(name)}
      </span>
    `;
  }

  function renderFamilyCard(family) {
    return `
      <button class="family-card" type="button" data-family-id="${family.id}">
        <div class="card-child">
          ${avatarMarkup({
            name: family.child.name_en,
            photoUrl: family.child.photo_url,
            sizeClass: "avatar-child",
            placeholderLabel: "",
            paletteIndex: family.colorIndex,
            completelyUnknown: !family.child.name_en,
          })}
          <div class="child-name">${nameTriggerMarkup(family.child.name_en)}</div>
          <div class="child-name-zh">${family.child.name_zh || "\u00a0"}</div>
        </div>
        <div class="card-divider"></div>
        <div class="parents-row">
          ${parentCardMarkup("爸爸", family.father, family.colorIndex)}
          ${parentCardMarkup("妈妈", family.mother, family.colorIndex)}
        </div>
      </button>
    `;
  }

  function renderGrid() {
    const items = filteredFamilies();
    familyGrid.innerHTML = items.length
      ? items.map(renderFamilyCard).join("")
      : `<div class="family-card" tabindex="-1"><div class="child-name">没有匹配结果</div><div class="child-name-zh">可以换个名字或关键词试试</div></div>`;

    familyGrid.querySelectorAll("[data-family-id]").forEach((node) => {
      node.addEventListener("click", () => openModal(node.getAttribute("data-family-id")));
    });
  }

  function chipMarkup(label) {
    return `<span class="chip">${label}</span>`;
  }

  function detailField(value, addLabel, type) {
    if (value) {
      if (type === "email") {
        return `<a class="ghost-link" href="mailto:${value}">${value}</a>`;
      }
      return `<span>${value}</span>`;
    }
    return `<button type="button" class="ghost-link">${addLabel}</button>`;
  }

  function renderParentDetail(role, parent, paletteIndex) {
    const placeholder = role === "爸爸" ? "爸" : "妈";
    return `
      <div class="detail-parent-card">
        <div class="parent-header">
          ${avatarMarkup({
            name: parent.name,
            photoUrl: parent.photo_url,
            sizeClass: "avatar-detail-parent",
            placeholderLabel: placeholder,
            paletteIndex,
            completelyUnknown: !parent.name,
          })}
          <div class="parent-heading">
            <span class="parent-role">${role}</span>
            <div class="detail-parent-name">${nameTriggerMarkup(parent.name || "待补姓名")}</div>
          </div>
        </div>
        <div class="detail-line">${detailField(parent.phone, "+ 添加电话")}</div>
        <div class="detail-line">${detailField(parent.email, "+ 添加邮箱", "email")}</div>
      </div>
    `;
  }

  function openModal(familyId) {
    selectedFamilyId = familyId;
    const family = families.find((item) => item.id === familyId);
    if (!family) return;

    const chips = [...family.child.tags];
    if (family.child.birthday) chips.push(`生日 ${family.child.birthday}`);

    modalContent.innerHTML = `
      <div class="modal-content">
        <div class="modal-header">
          <div class="modal-topline">
            ${avatarMarkup({
              name: family.child.name_en,
              photoUrl: family.child.photo_url,
              sizeClass: "avatar-detail",
              placeholderLabel: "",
              paletteIndex: family.colorIndex,
              completelyUnknown: !family.child.name_en,
            })}
            <div>
              <h2 class="modal-title" id="modal-title">${nameTriggerMarkup(family.child.name_en || "Unknown child")}</h2>
              <p class="modal-subtitle">${family.child.name_zh || "未填写中文名"} · ${family.child.class_name}</p>
              <div class="chips">
                ${chips.length ? chips.map(chipMarkup).join("") : chipMarkup("可继续补标签")}
              </div>
            </div>
          </div>
          <div class="modal-actions">
            <button type="button" class="modal-button" id="edit-button">编辑</button>
            <button type="button" class="modal-button close-button" data-close-modal="true" aria-label="关闭">×</button>
          </div>
        </div>

        <div class="detail-grid">
          ${renderParentDetail("爸爸", family.father, family.colorIndex)}
          ${renderParentDetail("妈妈", family.mother, family.colorIndex)}
        </div>

        <div class="notes-card">
          <p class="section-label">备注</p>
          ${
            family.notes
              ? `<p class="notes-body">${escapeHtml(family.notes)}</p>`
              : `<p class="notes-empty">还没有备注，可以补充语言背景、接送习惯、和谁玩得好等记忆点。</p>`
          }
        </div>

        <div class="fields-card">
          <p class="section-label">更多字段</p>
          <div class="field-actions">
            <button type="button" class="field-chip">+ 住址</button>
            <button type="button" class="field-chip">+ 兄弟姐妹</button>
            <button type="button" class="field-chip">+ 过敏</button>
            <button type="button" class="field-chip">+ 自定义</button>
          </div>
        </div>
      </div>
    `;

    modal.classList.remove("hidden");
    modal.setAttribute("aria-hidden", "false");
    bindPhotoButtons(modalContent);
    bindPronounceButtons(modalContent);
  }

  function closeModal() {
    modal.classList.add("hidden");
    modal.setAttribute("aria-hidden", "true");
  }

  function openLightbox(photoUrl, name) {
    if (!photoUrl) return;
    lightboxImage.src = photoUrl;
    lightboxImage.alt = name || "";
    lightbox.classList.remove("hidden");
    lightbox.setAttribute("aria-hidden", "false");
  }

  function closeLightbox() {
    lightbox.classList.add("hidden");
    lightbox.setAttribute("aria-hidden", "true");
    lightboxImage.src = "";
    lightboxImage.alt = "";
  }

  function bindPhotoButtons(scope) {
    scope.querySelectorAll("[data-photo-url]").forEach((node) => {
      node.addEventListener("click", (event) => {
        event.stopPropagation();
        openLightbox(node.getAttribute("data-photo-url"), node.getAttribute("data-photo-name") || "");
      });
      node.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          event.stopPropagation();
          openLightbox(node.getAttribute("data-photo-url"), node.getAttribute("data-photo-name") || "");
        }
      });
    });
  }

  function pronounceName(name) {
    const text = (name || "").trim();
    if (!text || !("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = /^[A-Za-z' -]+$/.test(text) ? "en-AU" : "zh-CN";
    window.speechSynthesis.speak(utterance);
  }

  function bindPronounceButtons(scope) {
    scope.querySelectorAll("[data-pronounce]").forEach((node) => {
      node.addEventListener("click", (event) => {
        event.stopPropagation();
        pronounceName(node.getAttribute("data-pronounce") || "");
      });
      node.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          event.stopPropagation();
          pronounceName(node.getAttribute("data-pronounce") || "");
        }
      });
    });
  }

  function createDraftFamily() {
    const nextIndex = families.length;
    const newFamily = {
      id: `draft-${Date.now()}`,
      colorIndex: nextIndex % palette.length,
      child: {
        name_en: "",
        name_zh: "",
        photo_url: "",
        birthday: "",
        tags: ["新建家庭"],
        class_name: "KL 2026",
      },
      father: { name: "", photo_url: "", phone: "", email: "" },
      mother: { name: "", photo_url: "", phone: "", email: "" },
      notes: "",
      custom_fields: {},
    };
    families = [newFamily, ...families];
    renderGrid();
    openModal(newFamily.id);
  }

  function escapeHtml(value) {
    return value
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function escapeAttribute(value) {
    return escapeHtml(value);
  }

  addFamilyButton.addEventListener("click", createDraftFamily);
  searchInput.addEventListener("input", renderGrid);

  modal.addEventListener("click", (event) => {
    const target = event.target;
    if (target instanceof HTMLElement && target.dataset.closeModal === "true") {
      closeModal();
    }
  });

  lightbox.addEventListener("click", (event) => {
    const target = event.target;
    if (target instanceof HTMLElement && target.dataset.closeLightbox === "true") {
      closeLightbox();
    }
  });

  window.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !modal.classList.contains("hidden")) {
      closeModal();
    }
    if (event.key === "Escape" && !lightbox.classList.contains("hidden")) {
      closeLightbox();
    }
  });

  renderGrid();
  bindPhotoButtons(document);
  bindPronounceButtons(document);
})();
