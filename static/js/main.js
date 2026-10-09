/**
 * YASHASWI RESIDENCY HOME STAY
 * Core Client-side Controller & Interactions
 */

document.addEventListener('DOMContentLoaded', () => {
  // --- 1. Sticky Navbar on Scroll ---
  const navbar = document.querySelector('.navbar');
  window.addEventListener('scroll', () => {
    if (window.scrollY > 50) {
      navbar?.classList.add('scrolled');
    } else {
      navbar?.classList.remove('scrolled');
    }
  }, { passive: true });

  // --- 2. Mobile Nav Toggle ---
  const mobileToggle = document.getElementById('mobile-toggle');
  const navMenu = document.getElementById('nav-menu');
  mobileToggle?.addEventListener('click', () => {
    navMenu?.classList.toggle('active');
  });

  document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', () => {
      navMenu?.classList.remove('active');
    });
  });

  // --- 3. 3D Card Tilt Effects ---
  const tiltCards = document.querySelectorAll('.room-card, .feature-pill, .amenity-card');
  tiltCards.forEach(card => {
    card.addEventListener('mousemove', (e) => {
      const rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left - rect.width / 2;
      const y = e.clientY - rect.top - rect.height / 2;
      const rotateX = (-y / rect.height) * 8;
      const rotateY = (x / rect.width) * 8;
      card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateY(-6px)`;
    });

    card.addEventListener('mouseleave', () => {
      card.style.transform = '';
    });
  });

  // --- 4. Gallery Filtering & Lightbox ---
  const filterBtns = document.querySelectorAll('.filter-btn');
  const galleryItems = document.querySelectorAll('.gallery-item');
  const lightboxModal = document.getElementById('lightbox-modal');
  const lightboxImg = document.getElementById('lightbox-img');
  const lightboxCaption = document.getElementById('lightbox-caption');
  const lightboxClose = document.getElementById('lightbox-close');
  const lightboxPrev = document.getElementById('lightbox-prev');
  const lightboxNext = document.getElementById('lightbox-next');

  let currentGalleryIndex = 0;
  let activeGalleryItems = Array.from(galleryItems);

  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const cat = btn.getAttribute('data-filter');

      galleryItems.forEach(item => {
        const itemCats = (item.getAttribute('data-category') || '').split(' ');
        if (cat === 'all' || itemCats.includes(cat)) {
          item.style.display = '';
        } else {
          item.style.display = 'none';
        }
      });
      activeGalleryItems = Array.from(galleryItems).filter(item => item.style.display !== 'none');
    });
  });

  function openLightbox(index) {
    if (!activeGalleryItems[index]) return;
    currentGalleryIndex = index;
    const item = activeGalleryItems[index];
    const img = item.querySelector('.gallery-img');
    const cap = item.querySelector('.gallery-caption');

    if (lightboxImg) lightboxImg.src = img.src;
    if (lightboxCaption) lightboxCaption.textContent = cap ? cap.textContent : '';
    lightboxModal?.classList.add('active');
    document.body.style.overflow = 'hidden';
  }

  function closeLightbox() {
    lightboxModal?.classList.remove('active');
    document.body.style.overflow = '';
  }

  galleryItems.forEach((item) => {
    item.addEventListener('click', () => {
      const idx = activeGalleryItems.indexOf(item);
      if (idx !== -1) openLightbox(idx);
    });
  });

  lightboxClose?.addEventListener('click', closeLightbox);
  lightboxPrev?.addEventListener('click', () => {
    const newIdx = (currentGalleryIndex - 1 + activeGalleryItems.length) % activeGalleryItems.length;
    openLightbox(newIdx);
  });
  lightboxNext?.addEventListener('click', () => {
    const newIdx = (currentGalleryIndex + 1) % activeGalleryItems.length;
    openLightbox(newIdx);
  });

  lightboxModal?.addEventListener('click', (e) => {
    if (e.target === lightboxModal) closeLightbox();
  });

  document.addEventListener('keydown', (e) => {
    if (!lightboxModal?.classList.contains('active')) return;
    if (e.key === 'Escape') closeLightbox();
    if (e.key === 'ArrowLeft') lightboxPrev?.click();
    if (e.key === 'ArrowRight') lightboxNext?.click();
  });

  // --- 5. Room Details Modal ---
  const roomModal = document.getElementById('room-details-modal');
  const roomModalClose = document.getElementById('room-modal-close');
  const roomModalTitle = document.getElementById('room-modal-title');
  const roomModalCategory = document.getElementById('room-modal-category');
  const roomModalPrice = document.getElementById('room-modal-price');
  const roomModalCapacity = document.getElementById('room-modal-capacity');
  const roomModalDesc = document.getElementById('room-modal-desc');
  const roomModalAmenities = document.getElementById('room-modal-amenities');
  const roomModalGallery = document.getElementById('room-modal-gallery');
  const roomModalBookBtn = document.getElementById('room-modal-book-btn');

  let activeModalRoom = null;

  document.querySelectorAll('.btn-view-room').forEach(btn => {
    btn.addEventListener('click', async () => {
      const roomId = btn.getAttribute('data-room-id');
      try {
        const res = await fetch(`/api/rooms/${roomId}`);
        const data = await res.json();
        if (data.success && data.room) {
          activeModalRoom = data.room;
          if (roomModalTitle) roomModalTitle.textContent = activeModalRoom.name;
          if (roomModalCategory) roomModalCategory.textContent = activeModalRoom.category + " Stay";
          if (roomModalPrice) roomModalPrice.textContent = `₹${activeModalRoom.price_per_night} / night`;
          if (roomModalCapacity) roomModalCapacity.textContent = `${activeModalRoom.capacity} Guests • ${activeModalRoom.bed_type}`;
          if (roomModalDesc) roomModalDesc.textContent = activeModalRoom.description;

          // Amenities
          if (roomModalAmenities) {
            roomModalAmenities.innerHTML = activeModalRoom.amenities.map(a =>
              `<span class="amenity-tag">✓ ${a}</span>`
            ).join('');
          }

          // Gallery photos
          if (roomModalGallery) {
            roomModalGallery.innerHTML = activeModalRoom.photos.map(p =>
              `<img src="${p}" alt="${activeModalRoom.name}" style="width: 100%; height: 260px; object-fit: cover; border-radius: 12px; margin-bottom: 0.75rem;">`
            ).join('');
          }

          if (roomModalBookBtn) {
            roomModalBookBtn.setAttribute('data-room-id', activeModalRoom.room_id);
          }

          roomModal?.classList.add('active');
          document.body.style.overflow = 'hidden';
        }
      } catch (err) {
        console.error('Error fetching room:', err);
      }
    });
  });

  roomModalClose?.addEventListener('click', () => {
    roomModal?.classList.remove('active');
    document.body.style.overflow = '';
  });

  roomModal?.addEventListener('click', (e) => {
    if (e.target === roomModal) {
      roomModal.classList.remove('active');
      document.body.style.overflow = '';
    }
  });

  // --- 6. Booking Modal & Flow ---
  const bookingModal = document.getElementById('booking-modal');
  const bookingModalClose = document.getElementById('booking-modal-close');
  const bookingForm = document.getElementById('booking-form');
  const bookingRoomSelect = document.getElementById('booking-room-select');
  const bookingCheckIn = document.getElementById('booking-check-in');
  const bookingCheckOut = document.getElementById('booking-check-out');
  const bookingAlert = document.getElementById('booking-alert');

  function openBookingModal(roomId = null, checkIn = '', checkOut = '', guests = '1') {
    if (roomModal?.classList.contains('active')) {
      roomModal.classList.remove('active');
    }
    if (roomId && bookingRoomSelect) {
      bookingRoomSelect.value = roomId;
    }
    if (checkIn && bookingCheckIn) bookingCheckIn.value = checkIn;
    if (checkOut && bookingCheckOut) bookingCheckOut.value = checkOut;
    const guestsField = document.getElementById('booking-guests');
    if (guests && guestsField) guestsField.value = guests;

    bookingAlert?.classList.add('d-none');
    bookingModal?.classList.add('active');
    document.body.style.overflow = 'hidden';
  }

  function closeBookingModal() {
    bookingModal?.classList.remove('active');
    document.body.style.overflow = '';
  }

  document.querySelectorAll('.btn-open-booking').forEach(btn => {
    btn.addEventListener('click', () => {
      const rid = btn.getAttribute('data-room-id');
      openBookingModal(rid);
    });
  });

  roomModalBookBtn?.addEventListener('click', () => {
    const rid = roomModalBookBtn.getAttribute('data-room-id');
    openBookingModal(rid);
  });

  bookingModalClose?.addEventListener('click', closeBookingModal);
  bookingModal?.addEventListener('click', (e) => {
    if (e.target === bookingModal) closeBookingModal();
  });

  // Floating Hero Availability Form
  const heroAvailForm = document.getElementById('hero-availability-form');
  heroAvailForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const cin = document.getElementById('hero-check-in')?.value;
    const cout = document.getElementById('hero-check-out')?.value;
    const guests = document.getElementById('hero-guests')?.value;

    if (!cin || !cout) {
      alert('Please select both Check-in and Check-out dates.');
      return;
    }
    if (new Date(cout) <= new Date(cin)) {
      alert('Check-out date must be after check-in date.');
      return;
    }

    // Scroll to rooms or open booking modal
    openBookingModal(null, cin, cout, guests);
  });

  // Handle Booking Form Submit
  bookingForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const submitBtn = bookingForm.querySelector('button[type="submit"]');
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerHTML = 'Verifying Availability...';
    }

    const payload = {
      guest_name: document.getElementById('booking-name')?.value.trim(),
      phone: document.getElementById('booking-phone')?.value.trim(),
      email: document.getElementById('booking-email')?.value.trim(),
      room_id: parseInt(bookingRoomSelect?.value),
      check_in: bookingCheckIn?.value,
      check_out: bookingCheckOut?.value,
      guests: parseInt(document.getElementById('booking-guests')?.value || '1'),
      special_requests: document.getElementById('booking-requests')?.value.trim()
    };

    try {
      const res = await fetch('/api/bookings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();

      if (!res.ok || !data.success) {
        if (bookingAlert) {
          bookingAlert.textContent = data.error || 'Booking could not be processed.';
          bookingAlert.classList.remove('d-none');
        }
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.innerHTML = 'Confirm Booking Request';
        }
        return;
      }

      // Success - show confirmation
      closeBookingModal();
      showConfirmationModal(data.booking, data.homestay_phone, data.whatsapp, data.upi_id, data.upi_enabled);
      bookingForm.reset();
    } catch (err) {
      if (bookingAlert) {
        bookingAlert.textContent = 'Server connection error. Please try again or call 087921 28459.';
        bookingAlert.classList.remove('d-none');
      }
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = 'Confirm Booking Request';
      }
    }
  });

  // --- 7. Confirmation Modal ---
  const confirmModal = document.getElementById('confirm-modal');
  const confirmModalClose = document.getElementById('confirm-modal-close');

  function showConfirmationModal(booking, phone, whatsapp, upiId, upiEnabled) {
    const idEl = document.getElementById('confirm-id');
    const guestEl = document.getElementById('confirm-guest');
    const roomEl = document.getElementById('confirm-room');
    const datesEl = document.getElementById('confirm-dates');
    const amountEl = document.getElementById('confirm-amount');
    const waBtn = document.getElementById('confirm-wa-btn');
    const upiInfo = document.getElementById('confirm-upi-info');

    if (idEl) idEl.textContent = booking.booking_id;
    if (guestEl) guestEl.textContent = booking.guest_name;
    if (roomEl) roomEl.textContent = `${booking.room_name} (${booking.room_category})`;
    if (datesEl) datesEl.textContent = `${booking.check_in} to ${booking.check_out} (${booking.number_of_nights} Night${booking.number_of_nights > 1 ? 's' : ''})`;
    if (amountEl) amountEl.textContent = `₹${booking.total_amount}`;

    // Pre-fill WhatsApp message
    const msg = encodeURIComponent(
      `Hello Yashaswi Residency Home Stay,\n\nI have submitted a booking request via your official website:\n• Booking ID: ${booking.booking_id}\n• Guest: ${booking.guest_name}\n• Room: ${booking.room_name}\n• Dates: ${booking.check_in} to ${booking.check_out}\n• Total Amount: ₹${booking.total_amount}\n\nPlease confirm availability and payment details. Thank you!`
    );
    const cleanWa = whatsapp ? whatsapp.replace(/[^0-9]/g, '') : '918792128459';
    if (waBtn) {
      waBtn.href = `https://wa.me/${cleanWa}?text=${msg}`;
    }

    if (upiInfo && upiEnabled && upiId) {
      upiInfo.innerHTML = `<strong>Official UPI Payment ID:</strong> <span style="color: #c69255; font-weight: 700;">${upiId}</span><br><small style="color: #64748b;">(GPay / PhonePe / Paytm accepted)</small>`;
      upiInfo.style.display = 'block';
    } else if (upiInfo) {
      upiInfo.style.display = 'none';
    }

    confirmModal?.classList.add('active');
    document.body.style.overflow = 'hidden';
  }

  confirmModalClose?.addEventListener('click', () => {
    confirmModal?.classList.remove('active');
    document.body.style.overflow = '';
  });

  // --- 8. Feedback / Review Submission Modal ---
  const feedbackModal = document.getElementById('feedback-modal');
  const feedbackModalClose = document.getElementById('feedback-modal-close');
  const btnOpenFeedback = document.getElementById('btn-open-feedback');
  const feedbackForm = document.getElementById('feedback-form');
  const feedbackAlert = document.getElementById('feedback-alert');
  const starItems = document.querySelectorAll('.star-item');
  const feedbackRatingInput = document.getElementById('feedback-rating');

  function openFeedbackModal() {
    if (feedbackAlert) feedbackAlert.style.display = 'none';
    feedbackModal?.classList.add('active');
    document.body.style.overflow = 'hidden';
  }

  function closeFeedbackModal() {
    feedbackModal?.classList.remove('active');
    document.body.style.overflow = '';
  }

  btnOpenFeedback?.addEventListener('click', openFeedbackModal);
  feedbackModalClose?.addEventListener('click', closeFeedbackModal);
  feedbackModal?.addEventListener('click', (e) => {
    if (e.target === feedbackModal) closeFeedbackModal();
  });

  // Interactive Star Rating Picker
  let currentRating = 5;
  starItems.forEach(star => {
    star.addEventListener('click', () => {
      currentRating = parseInt(star.getAttribute('data-val') || '5');
      if (feedbackRatingInput) feedbackRatingInput.value = currentRating;
      updateStars(currentRating);
    });

    star.addEventListener('mouseenter', () => {
      const hoverVal = parseInt(star.getAttribute('data-val') || '5');
      updateStars(hoverVal);
    });
  });

  document.getElementById('star-rating-picker')?.addEventListener('mouseleave', () => {
    updateStars(currentRating);
  });

  function updateStars(val) {
    starItems.forEach(s => {
      const sVal = parseInt(s.getAttribute('data-val') || '0');
      s.style.opacity = sVal <= val ? '1' : '0.25';
    });
  }

  // Handle Feedback Submission
  feedbackForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const submitBtn = document.getElementById('feedback-submit-btn');
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = 'Submitting Feedback...';
    }

    const payload = {
      guest_name: document.getElementById('feedback-name')?.value.trim(),
      rating: parseInt(feedbackRatingInput?.value || '5'),
      stay_date: document.getElementById('feedback-stay-date')?.value.trim() || 'Verified Guest',
      comment: document.getElementById('feedback-comment')?.value.trim()
    };

    try {
      const res = await fetch('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();

      if (res.ok && data.success) {
        if (feedbackAlert) {
          feedbackAlert.textContent = 'Thank you! Your feedback has been recorded successfully.';
          feedbackAlert.style.background = '#dcfce7';
          feedbackAlert.style.color = '#15803d';
          feedbackAlert.style.display = 'block';
        }

        // Dynamically prepend new review card
        const grid = document.getElementById('reviews-grid-container');
        if (grid) {
          const starsHtml = '★'.repeat(payload.rating);
          const initial = payload.guest_name[0] || 'G';
          const newCard = document.createElement('div');
          newCard.className = 'review-card';
          newCard.innerHTML = `
            <div class="review-card-stars">${starsHtml}</div>
            <div class="review-quote">"${payload.comment}"</div>
            <div class="reviewer-meta">
              <div class="reviewer-avatar">${initial}</div>
              <div style="text-align: left;">
                <div class="reviewer-name">${payload.guest_name}</div>
                <div class="reviewer-date">${payload.stay_date}</div>
              </div>
            </div>
          `;
          grid.insertBefore(newCard, grid.firstChild);
        }

        setTimeout(() => {
          feedbackForm.reset();
          closeFeedbackModal();
        }, 1500);
      } else {
        if (feedbackAlert) {
          feedbackAlert.textContent = data.error || 'Failed to submit feedback.';
          feedbackAlert.style.background = '#fee2e2';
          feedbackAlert.style.color = '#b91c1c';
          feedbackAlert.style.display = 'block';
        }
      }
    } catch (err) {
      if (feedbackAlert) {
        feedbackAlert.textContent = 'Connection error. Please try again.';
        feedbackAlert.style.background = '#fee2e2';
        feedbackAlert.style.color = '#b91c1c';
        feedbackAlert.style.display = 'block';
      }
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = 'SUBMIT FEEDBACK';
      }
    }
  });

  // --- Live Room Price Real-Time Simultaneous Synchronization ---
  async function syncRoomPrices() {
    try {
      const res = await fetch(`/api/rooms?all=1&_t=${Date.now()}`, { cache: 'no-store' });
      if (!res.ok) return;
      const data = await res.json();
      if (!data.success || !Array.isArray(data.rooms)) return;

      let minPrice = Infinity;

      data.rooms.forEach(r => {
        const p = parseFloat(r.price_per_night);
        if (!isNaN(p)) {
          if (p < minPrice) minPrice = p;

          // 1. Update room card price badge
          const priceBadge = document.getElementById(`price-val-${r.room_id}`);
          if (priceBadge) {
            const formatted = `₹${Math.round(p)}`;
            if (priceBadge.textContent.trim() !== formatted) {
              priceBadge.textContent = formatted;
              priceBadge.classList.add('price-flash');
              setTimeout(() => priceBadge.classList.remove('price-flash'), 1200);
            }
          }

          // 2. Update booking dropdown options
          const selectOpt = document.querySelector(`#booking-room-select option[value="${r.room_id}"]`);
          if (selectOpt) {
            selectOpt.textContent = `${r.name} (Starting ₹${Math.round(p)}/night)`;
          }

          // 3. Update room card dataset
          const card = document.querySelector(`.room-card[data-room-id="${r.room_id}"]`);
          if (card) {
            card.setAttribute('data-room-price', p);
          }
        }
      });

      // Update section header starting price
      if (minPrice !== Infinity) {
        const headerPrice = document.getElementById('header-starting-price');
        if (headerPrice) {
          const headerFormatted = `Starting from ₹${Math.round(minPrice)} / night`;
          if (headerPrice.textContent.trim() !== headerFormatted) {
            headerPrice.textContent = headerFormatted;
            headerPrice.classList.add('price-flash');
            setTimeout(() => headerPrice.classList.remove('price-flash'), 1200);
          }
        }

        // Update mobile sticky price
        const mobilePrice = document.getElementById('mobile-sticky-price');
        if (mobilePrice) {
          const mobFormatted = `₹${Math.round(minPrice)} / night`;
          if (mobilePrice.textContent.trim() !== mobFormatted) {
            mobilePrice.textContent = mobFormatted;
            mobilePrice.classList.add('price-flash');
            setTimeout(() => mobilePrice.classList.remove('price-flash'), 1200);
          }
        }
      }
    } catch (err) {
      // Non-blocking background sync
    }
  }

  // 1. Immediate sync on load
  syncRoomPrices();

  // 2. Continuous real-time polling every 5 seconds for cross-device updates
  setInterval(syncRoomPrices, 5000);

  // 3. BroadcastChannel for instant simultaneous updates across open tabs
  if ('BroadcastChannel' in window) {
    try {
      const roomChannel = new BroadcastChannel('yashaswi_room_sync');
      roomChannel.onmessage = (e) => {
        if (e.data && e.data.type === 'ROOM_PRICE_UPDATED') {
          syncRoomPrices();
        }
      };
    } catch (e) {}
  }

  // 4. Storage event for cross-window / cross-tab synchronization
  window.addEventListener('storage', (e) => {
    if (e.key === 'yashaswi_room_price_update') {
      syncRoomPrices();
    }
  });

  // 5. Visibility change to immediately sync when user switches back to this tab
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
      syncRoomPrices();
    }
  });
});
